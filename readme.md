# Points – A Red Discord Bot Cog

Points is a cog for [Red Discord Bot](https://docs.discord.red) that manages a points-based reward system. Users earn points through activity and can redeem them for rewards. Admins can manage user balances and customize rewards.

## Features

- Points tracking for users
- Rewards with customizable point costs
- Weekly and global leaderboards
- Admin and user command support

## Installation

1. Ensure Red Bot is installed and running.
2. Install this cog by placing it in your `cogs` directory or using a third-party repo setup.
3. Load the cog: [p] load points


## Commands

### User Commands

- `faq` – Posts the link to the FAQ Google Doc.
- `balance` – Check your current points balance.
- `commands` – List all available user commands.
- `luckyroll` – Test your luck to win points.
- `redeem` – Redeem a reward.
- `rewards` – List available rewards.
- `leaderboard` – Show the general leaderboard.

### Admin Commands

- `givepoints` – Give points to a user.
- `removepoints` – Remove points from a user.
- `setreward` – Set a reward with a required point cost.
- `removereward` – Remove a reward.
- `setrewardchannel` – Set the channel for reward redemption notifications.
- `setweeklychannel` - Set the channel for weekly leaderboard posting.
- `weeklyleaderboard` - Post weekly leaderboard without resetting it.
- `ResetWeekly` - Post the weekly leaderboard to the designated channel and reset the weekly leaderboard. 
- `userbalance` – Check current user points balance.

## Example Use Case

Let your community earn points for participating in chat or voice, then let them redeem those points for server perks like roles, shoutouts, or custom emojis.

---

This cog is a work in progress. Contributions, suggestions, and issues are welcome!
