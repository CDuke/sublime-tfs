# Sublime TFS Version History

## Changelog 0.0.11

**Features:**

- Add command `Move`

## Changelog 0.0.10

**Features:**

- Add command `Shelve...` (Issue #23)
- `History...` command is now recursive on directories

**Bugfix:**

- Issue #20 (thanks to `Mathieu DARTIGUES`)

## Changelog 0.0.9

**Features:**

- new commands in side-bar: `Checkout`, `History...` (thanks to `Mathieu DARTIGUES`)
- all side-bar commands can be executed on `files` and `directories`
- Add setting `always_is_graph` to fix Issue #19
- Add setting `auto_checkout_timeout` (thanks to `Mathieu DARTIGUES`)

## Changelog 0.0.8

**Features:**

- Add command `Set TFS Credentials...` (Issue #16)
- Add settings `tfs_username`, `tfs_password`

## Changelog 0.0.7

**Features:**

- Add command `Checkin...` to side-bar - can be executed on first selected directory (Issue #14)

## Changelog 0.0.6

**Features:**

- Add command `Get Latest Version` to side-bar (Issue #5)
- Add command `Checkout Open Files` to TFS Menu and Context Menu
- Add new setting `auto_checkout_enabled`

**Bugfix:**

- Change autocheckout mechanism. Now it's raised `on_pre_save` event. (Issue #9)
- Working Directory for `tf.exe` and `tfpt.exe` is now calculationg from its path. (Issue #10)

## Changelog 0.0.5

**Features:**

- Add support Sublime text 3

## Changelog 0.0.4

**Features:**

- Add command `Annotate...`
- Add `Auto checkout` mode
- Add context menu

**Bugfix:**

- Small bugfix and typo

## Changelog 0.0.3

**Bugfix:**

- Check that file is readonly before save it

## Changelog 0.0.2

**Features:**

- Added autosave on checkin, get latest, compare with latest

## Changelog 0.0.1

**Features:**

- Checkout file
- Checkin file
- Get latest version file
- View history of file
- Compare file with version
- Undo changes in file
- Check file status
- Add file
- Delete file
