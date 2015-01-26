# [Sublime TFS](https://bitbucket.org/CDuke/sublime-tfs)

Sublime TFS is a plugin for the wonderful text editor [Sublime Text 2](http://sublimetext.com/2) and [Sublime Text 3](http://sublimetext.com/3).

## Overview

Plugin adds **TFS** menu to `Main.sublime-menu`.

Plugin adds the following commands to `Context.sublime-menu`:

- **Checkout**               - Checkout current file
- **Undo**                   - Undo changes in current file
- **Checkin...**             - Show checkin current file dialog
- **History...**             - Show current file history
- **Add**                    - Add current file to TFS
- **Get Latest Version**     - Get latest version of current file
- **Compare With Latest...** - Compare current file with latest version
- **Delete**                 - Delete current file from TFS (remove file from storage too)
- **Status**                 - Check current file TFS status
- **Annotate...**            - Annotate (blame)
- **Checkout Open Files**    - Checkout all open files

Plugin adds the following commands to `Side Bar.sublime-menu`:

- **Get Latest Version**     - Get latest version of selected in SideBar folder

## Settings

### [tf_path]

It specifies path to Team Foundation **(TF.exe)**. Mandatory for all commands.

Usually it's in:

* **x86** - `C:\Program Files\Microsoft Visual Studio 10.0\Common7\IDE\TF.exe`
* **x64** - `C:\Program Files (x86)\Microsoft Visual Studio 10.0\Common7\IDE\TF.exe`

### [tfpt_path]

It specifies path to TFS Power Tools **(TFPT.exe)**. Mandatory for **Annotate** command.

Usually it's in:

* **x64** - `C:\Program Files (x86)\Microsoft Team Foundation Server 2010 Power Tools\TFPT.exe`
* **x86** - `C:\Program Files\Microsoft Team Foundation Server 2010 Power Tools\TFPT.exe`

### [auto_checkout_enabled]

If `auto_checkout_enabled` is set to `false` - Sublime Text will show confirmation prompt on every checkout attempt, otherwise it will attempt checkout file on modification/save silently.

### [tfs_username] and [tfs_password]

Provide custom credentials to access TFS.

You can set only `tfs_username` in settings file and provide `tfs_password` on each Sublime session with `Set TFS Credentials...` command from Context menu or Main menu.


## Usage

For almost all commands, except **Add**, the current file should be under TFS version control.
After opening a file, you can execute a command in main menu **TFS** or from context menu.
