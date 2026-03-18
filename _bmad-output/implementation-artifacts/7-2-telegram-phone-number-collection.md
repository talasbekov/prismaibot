# Story 7.2: Implement phone number collection in Telegram bot

Status: done

## Story

As a пользователь из Казахстана,
I want чтобы бот мог запросить мой номер телефона для выставления счета в Kaspi,
So that я мог оплатить подписку удобным мне способом.

## Acceptance Criteria

1. **Given** the user selects "Оплатить через Kaspi" (or clicks the payment button from Story 4.2), **When** the bot responds, **Then** it must include a `ReplyKeyboardMarkup` with a button `request_contact=True`. [Source: tech-spec-apipay-kaspi-integration.md]

2. **Given** the phone number request message, **When** the user clicks "Отправить номер телефона", **Then** the bot must receive the `contact` update and extract the `phone_number`. [Source: Telegram Bot API]

3. **Given** a received phone number, **When** it is processed, **Then** the bot should inform the user that the invoice is being created. [Source: tech-spec-apipay-kaspi-integration.md]

4. **Given** an invalid or manual phone number entry (if the user types it), **When** the system receives it, **Then** it should attempt to normalize it to the format `8XXXXXXXXXX` (Kaspi requirement) or ask the user to use the button. [Source: apipay.kz/docs.html]

## Tasks / Subtasks

- [x] Add "Оплатить через Kaspi" button to paywall response in `billing/service.py`.
- [x] Implement `_handle_contact` logic in `conversation/session_bootstrap.py`.
- [x] Update `handle_session_entry` to route `contact` updates.
- [x] Implement phone number normalization utility.

## Dev Notes

- Use `KeyboardButton(text="📱 Отправить номер для Kaspi", request_contact=True)`.
- Re-use `IncomingMessage` schema if needed to store contact data temporarily.
- Ensure the user can cancel the process and return to the main menu.

## References

- Tech Spec: `_bmad-output/implementation-artifacts/tech-spec-apipay-kaspi-integration.md`
