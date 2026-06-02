# AURELIUS Telegram Migration

ANIMA is deprecated. AURELIUS owns Telegram assistant operations.

The active Telegram entrypoint is `_ARBITER/Bot/aurelius_bot.py`. It resolves
Msty through `integrations/msty/aurelius_provider.py` and uses
`AURELIUS_MSTY_BASE_URL`. The Telegram bootstrap does not import IBKR. Market
data and broker operations belong behind AETERNUM and the integration layer.

Scheduled operations:

- Morning Brief at `08:00`
- End-of-Day Shutdown at `18:00`

Startup requires `TELEGRAM_BOT_TOKEN`. Set `AURELIUS_TELEGRAM_CHAT_ID` for
scheduled delivery, or send `/start` after the bot launches to register the
active chat for the current process. A missing or unavailable Msty endpoint is
logged once and does not emit repeated scheduled Telegram errors.

The retired ANIMA implementation is preserved at
`archive/legacy_bots/anima_bot.py` for historical reference only.
