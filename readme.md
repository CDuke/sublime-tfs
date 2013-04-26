# Overview
Sublime TFS is a plugin for the wonderful text editor [Sublime Text 2](http://sublimetext.com/2).

It has base commands:
- Checkout file
- Checkin file
- Get latest version file
- View history of file
- Compare file with version
- Undo changes in file
- Check file status
- Add file
- Delete file
- Annotate (Blame)

# Settings
After installation, the "tf_path" setting must be set. It specifies the path to tf.exe. Usually it's in *C:\Program Files (x86)\Microsoft Visual Studio 10.0\Common7\IDE\TF.exe* for x64 and *C:\Program Files\Microsoft Visual Studio 10.0\Common7\IDE\TF.exe for x86*.

The Annotate command requires the TFS Power Tools. You must set the "tfpt_path" setting to the path to TFPT.exe. Usually it's in *C:\Program Files (x86)\Microsoft Team Foundation Server 2010 Power Tools\TFPT.exe* for x64 and *C:\Program Files\Microsoft Team Foundation Server 2010 Power Tools\TFPT.exe* for x86.

# Usage
For almost all commands, except Add, the current file should be under TFS version control. After opening a file, you can execute a command in main menu "TFS".