# Palworld Save Transfer

> ### :warning: This tool is experimental. Be careful of data loss and *always* make a backup.

This is a fork and modified from [palworld-host-save-fix](https://github.com/xNul/palworld-host-save-fix), all thanks to that repo for this work.

Palworld save files are different depending on the type of server you are running. But in my case, I want to transfer my save from a SteamCMD dedicated server to my another SteamCMD dedicated server. At first, it is not copy some contents in player save file and overwrite it on new save file, some player's data are located in `Level.sav` too.

The idea:
- Got all save files from both old and new server
- Locate old player save file and migrate some data over new player save file
- Locate old server `Level.sav` and migrate date related to this player to new `Level.sav`

## Usage

Dependencies:
- Python 3
- [uesave-rs](https://github.com/trumank/uesave-rs)

Command:
`python save-transfer.py <uesave.exe> <guide_file>`
`<uesave.exe>` - Path to your uesave.exe
`<guide_file>` - Path to your guidance source and dest save files, place this file at same directory with 2 both server save folder. Checkout example file in repo

Example:
`python save-transfer.py $HOME/.cargo/bin/uesave ~/Desktop/Palworld/transfer.yaml`

### Appreciate any help testing and resolving bugs.