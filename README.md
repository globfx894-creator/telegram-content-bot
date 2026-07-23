# Telegram Content Bot

A powerful Telegram bot for managing and sharing content across 11 categories with daily limits, auto-delete, and enterprise protection.

## Features

### 📊 Categories (11)
- 📸 Photos (2 taps/day)
- 🇮🇳🇵🇰 India & Pakistan (3 taps/day)
- 📁 Files (1 tap/day)
- 🔗 Links (1 tap/day)
- 🎥 Candid (2 taps/day, 10 videos/tap)
- 📹 CCTV (2 taps/day, 10 videos/tap)
- 🇬🇧 English (2 taps/day, 13 videos/tap)
- 🎞️ Cppz (2 taps/day, 15 videos/tap)
- 🏳️‍🌈 Gay (2 taps/day, 10 videos/tap)
- 🌑 Dark (2 taps/day, 2 videos/tap)
- 👩‍❤️‍👩 Lesbo (2 taps/day, 13 videos/tap)

### 🛡️ Protection Features
- Anti-Spam Protection
- Anti-Flood Protection  
- Rate Limiting
- Blacklist System
- Temporary Bans (24h/48h/7d)
- Admin Logs
- Auto Backup
- Auto-Delete (24 hours)

### 👑 Admin Commands
- `/stats` - Bot statistics
- `/add <category>` - Add video
- `/videos <category>` - View videos
- `/remove <category> <index>` - Remove video
- `/grant <category> <user_id> <count>` - Grant extra taps
- `/blacklist <user_id>` - Block user
- `/unblacklist <user_id>` - Unblock user
- `/logs` - View admin logs
- `/protect` - Toggle protection

## Deployment

### Environment Variables
