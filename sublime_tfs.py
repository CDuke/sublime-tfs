import sublime
import sublime_plugin
# ------------------------------
import threading
import locale
import subprocess
import os
import stat
import sys
# ------------------------------
OS_ENCODING = locale.getpreferredencoding()
IS_PYTHON_2 = (sys.hexversion < 0x03000000)
IS_PYTHON_3 = (sys.hexversion > 0x03000000)
# ------------------------------
def encode_to_OS(s, default=None):
    return s.encode(OS_ENCODING) if not s is None else default
def encode_all_to_OS(strings):
    return map(lambda s: encode_to_OS(s), strings)
def decode_from_OS(s, default=None):
    return s.decode(OS_ENCODING) if not s is None else default
# ------------------------------
def is_readonly(path):
    try:
        return not os.stat(path)[0] & stat.S_IWRITE
    except WindowsError:
        pass
# ------------------------------------------------------------
class TfsCredentials(object):
    username = None
    password = None
    def __init__(self):
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.username = settings.get("tfs_username", None)
        self.password = settings.get("tfs_password", None)
    def is_empty(self):
        return self.username is None
    def get_username(self):
         return self.username if self.username is not None else ''
    def get_password(self):
         return self.password if self.password is not None else ''
# ------------------------------------------------------------
class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")
        self.tfpt_path = settings.get("tfpt_path")
        self.auto_checkout_enabled = settings.get("auto_checkout_enabled", True)

    def is_under_tfs(self, path):
        return self.status(path)

    def checkout(self, path):
        if self.auto_checkout_enabled or sublime.ok_cancel_dialog("Checkout " + path + "?"):
            return self.run_command(["checkout"], path)
        else:
            return (False, "Checkout is cancelled by user!")

    def checkin(self, path):
        return self.run_command(["checkin", "/recursive"], path, True)

    def undo(self, path):
        return self.run_command(["undo"], path)

    def history(self, path):
        return self.run_command(["history"], path, True)

    def add(self, path):
        return self.run_command(["add"], path)

    def get_latest(self, path):
        return self.run_command(["get", "/recursive"], path)

    def difference(self, path):
        return self.run_command(["difference"], path, True)

    def delete(self, path):
        return self.run_command(["delete"], path)

    def status(self, path):
        return self.run_command(["status"], path)

    def annotate(self, path):
        return self.run_command(["annotate"], path, True, True)

    def auto_checkout(self, path):
        return self.checkout(path) if self.status(path)[0] else (False, "")

    def run_command(self, command, path, is_graph = False, is_tfpt = False):
        try:
            global credentials
            current_dir = os.getcwd()
            executable = self.tfpt_path if is_tfpt else self.tf_path
            working_dir = os.path.dirname(executable)
            commands = [executable] + command + [path]
            # ------------------------------
            commands_with_credentials = list(commands)
            if not credentials.is_empty():
                commands_with_credentials = commands + ['/login:%s,%s' % (credentials.get_username(), credentials.get_password())]
            # ------------------------------
            os.chdir(working_dir)
            # !_! print("commands: [%s]\nis_graph: [%s]\nworking_dir: [%s]" % (commands, is_graph, working_dir))
            return self.__run_command(commands_with_credentials, is_graph)
        except Exception:
            print("commands: [%s]\nis_graph: [%s]\nworking_dir: [%s]" % (commands, is_graph, working_dir))
            raise
        finally:
            os.chdir(current_dir)

    def __run_command(self, commands, is_graph):
        if IS_PYTHON_2:
            commands = encode_all_to_OS(commands) # popen fails on unicode in py2.7
        if (is_graph):
            p = subprocess.Popen(commands)
        else:
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(commands, stderr=subprocess.PIPE, stdout=subprocess.PIPE, startupinfo=startup_info)
        (out, err) = p.communicate()
        if p.returncode == 0:
            print(out)
            return True, decode_from_OS(out, None)
        else:
            return False, decode_from_OS(err, "Unknown error")
# ------------------------------------------------------------
class TfsRunnerThread(threading.Thread):
    def __init__(self, path, method):
        super(TfsRunnerThread, self).__init__()
        self.method = method
        self.m_path = path
        self.success = False
        self.message = ""

    def run(self):
        (self.success, self.message) = self.method(self.m_path)
# ------------------------------------------------------------
class ThreadProgress():
    def __init__(self, view, thread, message, success_message = None):
        self.view = view
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        # ------------------------------
        if not self.thread.is_alive():
            # ------------------------------
            if self.view:
                self.view.erase_status('tfs')
            else:
                sublime.status_message('')
            # ------------------------------
            if not self.thread.success:
                sublime.status_message(self.thread.message)
                # sublime.message_dialog(self.thread.message)
            else:
                sublime.status_message(self.success_message if not self.success_message is None else self.thread.message)
                # sublime.message_dialog(self.success_message if not self.success_message is None else self.thread.message)
            # ------------------------------
            return
        # ------------------------------
        before = i % self.size
        after = (self.size - 1) - before
        msg = '%s [%s=%s]' % (self.message, ' ' * before, ' ' * after)
        # ------------------------------
        if self.view:
            self.view.set_status('tfs', msg)
        else:
            sublime.status_message(msg)
        # ------------------------------
        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend
        sublime.set_timeout(lambda: self.run(i), 100)
# ------------------------------------------------------------
class TfsCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkout)
            thread.start()
            ThreadProgress(self.view, thread, "Checkout...", "Checkout success: %s" % path)
class TfsUndoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.undo)
            thread.start()
            ThreadProgress(self.view, thread, "Undo...", "Undo success: %s" % path)
class TfsCheckinCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            if (not is_readonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkin)
            thread.start()
            ThreadProgress(self.view, thread, "Checkin...", "Checkin success: %s" % path)
class TfsDirCheckinCommand(sublime_plugin.WindowCommand): # used in SideBar - must be WindowCommand
    def is_visible(self, dirs):
        return (dirs != None) and (len(dirs) > 0) and all(os.path.isdir(item) for item in dirs)
    def run(self, dirs):
        path = dirs[0] # do Checkin for first selected directory only
        thread = TfsRunnerThread(path, TfsManager().checkin)
        thread.start()
        ThreadProgress(self.window.active_view(), thread, "Checkin dir: %s..." % path, "Checkin success: %s" % path)
class TfsHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.history)
            thread.start()
            ThreadProgress(self.view, thread, "History...", "History success: %s" % path)
class TfsAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.add)
            thread.start()
            ThreadProgress(self.view, thread, "Adding...", "Added success: %s" % path)
class TfsGetLatestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            if (not is_readonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting...", "Get latest success: %s" % path)
class TfsDirGetLatestCommand(sublime_plugin.WindowCommand): # used in SideBar - must be WindowCommand
    def is_visible(self, dirs):
        return (dirs != None) and (len(dirs) > 0) and all(os.path.isdir(item) for item in dirs)
    def run(self, dirs):
        path = dirs[0] # do GLV for first selected directory only
        manager = TfsManager()
        thread = TfsRunnerThread(path, manager.get_latest)
        thread.start()
        ThreadProgress(self.window.active_view(), thread, "Getting dir: %s..." % path, "Directory get latest success: %s" % path)
class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            if (not is_readonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.difference)
            thread.start()
            ThreadProgress(self.view, thread, "Comparing...", "Comparing success: %s" % path)
class TfsDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.delete)
            thread.start()
            ThreadProgress(self.view, thread, "Deleting...", "Delete success: %s" % path)
class TfsStatusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.status)
            thread.start()
            ThreadProgress(self.view, thread, "Getting status...")
class TfsAnnotateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.annotate)
            thread.start()
            ThreadProgress(self.view, thread, "Annotating...", "Annotate done")
class TfsEventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if not hasattr(self, 'manager'):
            self.manager = TfsManager()

        if self.manager.auto_checkout_enabled:
            path = view.file_name()
            if not (path is None):
                if is_readonly(path):
                    thread = TfsRunnerThread(path, self.manager.auto_checkout)
                    thread.start()
                    ThreadProgress(view, thread, "Checkout...", "Checkout success: %s" % path)
                    thread.join(5) #5 seconds. It's enough for auto-checkout.
                    if thread.isAlive():
                        sublime.set_timeout(lambda: "Checkout failed. Too long operation")
class TfsCheckoutOpenFilesCommand(sublime_plugin.WindowCommand):
    """
    Checkout all opened files
    """
    def run(self):
        for view in self.window.views():
            view.run_command('tfs_checkout')
# ------------------------------------------------------------
class TfsQueryCredentialsCommand(sublime_plugin.WindowCommand):
    """
    Query TFS credentials from user
    """
    def run(self):
        global credentials
        self.window.show_input_panel('Input TFS user name:', credentials.get_username(), self.on_done_username, lambda i: None, lambda: None)

    def on_done_username(self, s):
        global credentials
        credentials.username = s
        self.window.show_input_panel('Input TFS password:', '', self.on_done_password, lambda i: None, lambda: None)

    def on_done_password(self, s):
        global credentials
        credentials.password = s

# ------------------------------------------------------------
credentials = TfsCredentials()
# ------------------------------------------------------------
