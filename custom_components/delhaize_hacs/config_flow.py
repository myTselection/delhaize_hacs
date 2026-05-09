"""Config flow for the Delhaize integration."""

from __future__ import annotations

from typing import Any

from aiohttp.client_exceptions import ClientError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_AUTO_ACTIVATE_OFFERS,
    CONF_COOKIE,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    NAME,
)
from .delhaizeApi import (
    DelhaizeApi,
    DelhaizeApiError,
    DelhaizeAuthError,
    DelhaizeCaptchaRequired,
    DelhaizeMfaRequired,
    DelhaizeRequestError,
)

LANGUAGE_OPTIONS = ["nl", "fr", "en"]
CONF_OTP_CODE = "otp_code"


def _user_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user step schema."""
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Optional(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_COOKIE, default=defaults.get(CONF_COOKIE, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_LANGUAGE,
                default=defaults.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            ): SelectSelector(SelectSelectorConfig(options=LANGUAGE_OPTIONS)),
            vol.Required(
                CONF_AUTO_ACTIVATE_OFFERS,
                default=defaults.get(CONF_AUTO_ACTIVATE_OFFERS, False),
            ): BooleanSelector(),
        }
    )


MFA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OTP_CODE): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        )
    }
)


class DelhaizeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Delhaize."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._pending_api: DelhaizeApi | None = None
        self._pending_input: dict[str, Any] | None = None
        self._mfa_token: str | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_user_schema())

        data = _clean_input(user_input)
        has_cookie = bool(data.get(CONF_COOKIE))
        has_credentials = bool(data.get(CONF_USERNAME) and data.get(CONF_PASSWORD))
        if not has_cookie and not has_credentials:
            errors["base"] = "missing_auth"
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(data),
                errors=errors,
            )

        api = DelhaizeApi(
            async_get_clientsession(self.hass),
            cookie_header=data.get(CONF_COOKIE),
            language=data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        )

        try:
            customer = await self._authenticate(api, data, has_credentials)
        except DelhaizeMfaRequired as err:
            if not err.mfa_token:
                errors["base"] = "mfa_required"
            else:
                self._pending_api = api
                self._pending_input = data
                self._mfa_token = err.mfa_token
                await _try_send_mfa_code(api, err, data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))
                return self.async_show_form(step_id="mfa", data_schema=MFA_SCHEMA)
        except DelhaizeCaptchaRequired:
            errors["base"] = "captcha_required"
        except DelhaizeAuthError:
            errors["base"] = "login_failed"
        except (DelhaizeRequestError, ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except DelhaizeApiError:
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(data),
                errors=errors,
            )

        return await self._create_delhaize_entry(data, customer, api)

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication."""
        entry_id = self.context.get("entry_id")
        if entry_id:
            self._reauth_entry = self.hass.config_entries.async_get_entry(entry_id)

        return await self.async_step_user(
            {
                CONF_USERNAME: entry_data.get(CONF_USERNAME, ""),
                CONF_LANGUAGE: entry_data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                CONF_AUTO_ACTIVATE_OFFERS: entry_data.get(CONF_AUTO_ACTIVATE_OFFERS, False),
            }
        )

    async def async_step_mfa(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a Delhaize MFA one-time password."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(step_id="mfa", data_schema=MFA_SCHEMA)

        if not self._pending_api or not self._pending_input or not self._mfa_token:
            return self.async_abort(reason="mfa_session_expired")

        try:
            await self._pending_api.login_with_mfa(
                str(user_input[CONF_OTP_CODE]).strip(),
                self._mfa_token,
                lang=self._pending_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            )
            customer = await self._pending_api.validate_session()
        except DelhaizeCaptchaRequired:
            errors["base"] = "captcha_required"
        except DelhaizeAuthError:
            errors["base"] = "login_failed"
        except (DelhaizeRequestError, ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
        except DelhaizeApiError:
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="mfa",
                data_schema=MFA_SCHEMA,
                errors=errors,
            )

        return await self._create_delhaize_entry(
            self._pending_input,
            customer,
            self._pending_api,
        )

    async def _authenticate(
        self,
        api: DelhaizeApi,
        data: dict[str, Any],
        has_credentials: bool,
    ) -> dict[str, Any]:
        """Authenticate with cookie or credentials and return the customer."""
        if data.get(CONF_COOKIE):
            try:
                return await api.validate_session()
            except DelhaizeAuthError:
                if not has_credentials:
                    raise

        await api.login(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            lang=data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        )
        return await api.validate_session()

    async def _create_delhaize_entry(
        self,
        data: dict[str, Any],
        customer: dict[str, Any],
        api: DelhaizeApi,
    ) -> config_entries.ConfigFlowResult:
        """Create or update the Delhaize config entry."""
        unique_id = (
            customer.get("customerIdHash")
            or customer.get("uid")
            or data.get(CONF_USERNAME)
            or NAME
        )
        await self.async_set_unique_id(str(unique_id))

        cookie_header = api.get_cookie_header()
        entry_data = dict(data)
        if cookie_header:
            entry_data[CONF_COOKIE] = cookie_header

        if self._reauth_entry:
            if self._reauth_entry.unique_id and self._reauth_entry.unique_id != str(unique_id):
                return self.async_abort(reason="wrong_account")

            self.hass.config_entries.async_update_entry(self._reauth_entry, data=entry_data)
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        self._abort_if_unique_id_configured(updates=entry_data)

        title = _entry_title(customer, data)
        return self.async_create_entry(title=title, data=entry_data)


async def _try_send_mfa_code(
    api: DelhaizeApi,
    err: DelhaizeMfaRequired,
    language: str,
) -> None:
    """Try to trigger sending an MFA code."""
    try:
        await api.send_login_mfa_otp_code(
            err.mfa_token or "",
            mfa_purpose=err.mfa_purpose or "LOGIN",
            lang=language,
        )
    except DelhaizeApiError:
        pass


def _clean_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Trim blank optional values from config flow input."""
    data = dict(user_input)
    for key in (CONF_USERNAME, CONF_PASSWORD, CONF_COOKIE):
        value = data.get(key)
        if isinstance(value, str):
            value = value.strip()
        if value:
            data[key] = value
        else:
            data.pop(key, None)
    data.setdefault(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    data.setdefault(CONF_AUTO_ACTIVATE_OFFERS, False)
    return data


def _entry_title(customer: dict[str, Any], data: dict[str, Any]) -> str:
    """Build a friendly config entry title."""
    full_name = " ".join(
        value
        for value in (customer.get("firstName"), customer.get("lastName"))
        if value
    ).strip()
    if full_name:
        return f"{NAME} {full_name}"
    if data.get(CONF_USERNAME):
        return f"{NAME} {data[CONF_USERNAME]}"
    return NAME
