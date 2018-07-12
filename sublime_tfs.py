import sublime
import sublime_plugin
# ------------------------------
import datetime
import locale
import os
import stat
import subprocess
import sys
import threading
# ------------------------------
OS_ENCODING = locale.getpreferredencoding()
IS_PYTHON_2 = (sys.hexversion < 0x03000000)
IS_PYTHON_3 = (sys.hexversion > 0x03000000)
# ------------------------------
TRACE_INFO_ENABLED = False
TRACE_ERROR_ENABLED = True
# ------------------------------
def encode_to_OS(s, default=None):
    return s.encode(OS_ENCODING) if not s is None else default
def encode_all_to_OS(strings):
    return map(lambda s: encode_to_OS(s), strings)
def decode_from_OS(s, default=None):
    return s.decode(OS_ENCODING) if not s is None else default
def get_file_name(view):
    return view.file_name() if view else None
def save_view(view):
    path = get_file_name(view)
    if path and not is_readonly(path):
        view.run_command('save')
def trace_info(s):
    if TRACE_INFO_ENABLED:
        print(s)
def trace_error(s):
    if TRACE_ERROR_ENABLED:
        print(s)
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
         return self.username or ''
    def get_password(self):
         return self.password or ''
# ------------------------------------------------------------
class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")
        self.tfpt_path = settings.get("tfpt_path")
        self.auto_checkout_enabled = settings.get("auto_checkout_enabled", True)
        self.auto_checkout_timeout = settings.get("auto_checkout_timeout", 5)
        self.always_is_graph = settings.get("allways_is_graph", settings.get("always_is_graph", False)) # `allways` is typo but someone could use it already...

    def is_under_tfs(self, path):
        return self.status(path)

    def __is_recursive(self, path):
        return ["/recursive"] if os.path.isdir(path) else []

    def checkout(self, path):
        if self.auto_checkout_enabled or sublime.ok_cancel_dialog("Checkout " + path + "?"):
            commands = ["checkout"] + self.__is_recursive(path)
            return self.run_command(commands, path, is_graph = self.always_is_graph)
        else:
            return (False, "Checkout is cancelled by user!")

    def checkin(self, path):
        commands = ["checkin"] + self.__is_recursive(path)
        return self.run_command(commands, path, is_graph = True)

    def undo(self, path):
        return self.run_command(["undo"], path, is_graph = self.always_is_graph)

    def history(self, path):
        commands = ["history"] + self.__is_recursive(path)
        return self.run_command(commands, path, is_graph = True)

    def add(self, path):
        return self.run_command(["add"], path, is_graph = self.always_is_graph)

    def get_latest(self, path):
        commands = ["get"] + self.__is_recursive(path)
        return self.run_command(commands, path, is_graph = self.always_is_graph)

    def difference(self, path):
        return self.run_command(["difference"], path, is_graph = True)

    def delete(self, path):
        return self.run_command(["delete"], path, is_graph = self.always_is_graph)

    def status(self, path):
        return self.run_command(["status"], path, is_graph = self.always_is_graph)

    def shelve(self, path):
        # ------------------------------
        dname, fname = os.path.split(path)
        shelveset_name = fname[:200] + ' ' + datetime.datetime.now().strftime('[%Y-%m-%dT%H-%M]')
        # ------------------------------
        commands = ["shelve", "/replace", '/comment:' + shelveset_name, "/validate", shelveset_name, path] + self.__is_recursive(path)
        return self.run_command(commands, '', is_graph = True)

    def move(self, from_path, to_path):
        is_ok, msg = self.run_command(["move", from_path, to_path], '')
        try:
            window = sublime.active_window()
            if is_ok and window:
                view = window.active_view()
                if view and view.file_name() == from_path:
                    window.run_command("close")
                window.open_file(to_path)
        except Exception:
            pass
        return is_ok, msg

    def annotate(self, path):
        return self.run_command(["annotate"], path, is_graph = True, is_tfpt = True)

    def auto_checkout(self, path):
        return self.checkout(path) if self.status(path)[0] else (False, "")

    def run_command(self, command, path, is_graph = False, is_tfpt = False):
        try:
            # ------------------------------
            global credentials
            # ------------------------------
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
            trace_info("commands: [%s]\nis_graph: [%s]\nworking_dir: [%s]" % (commands, is_graph, working_dir))
            return self.__run_command(commands_with_credentials, is_graph)
        except Exception:
            trace_error("commands: [%s]\nis_graph: [%s]\nworking_dir: [%s]" % (commands, is_graph, working_dir))
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
            status_message = ''
            if self.thread.success:
                status_message = self.success_message or self.thread.message or 'Success.'
            else:
                status_message = self.thread.message
            # ------------------------------
            sublime.status_message(status_message)
            #!_! sublime.message_dialog(status_message)
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
        # ------------------------------
        sublime.set_timeout(lambda: self.run(i), 100)
# ------------------------------------------------------------
class TfsCheckoutCommand(sublime_plugin.WindowCommand):
    def run(self, path=None, view=None):
        view = view or self.window.active_view()
        path = path or get_file_name(view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().checkout)
            thread.start()
            ThreadProgress(view, thread, "Checkout: %s..." % path, "Checkout success: %s" % path)
class TfsFilesCheckoutCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        paths = (files or []) + (dirs or [])
        if paths:
            TfsCheckoutCommand(self.window).run(paths[0])
class TfsUndoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_file_name(self.view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().undo)
            thread.start()
            ThreadProgress(self.view, thread, "Undo: %s..." % path, "Undo success: %s" % path)
class TfsCheckinCommand(sublime_plugin.WindowCommand):
    def run(self, path=None):
        view = self.window.active_view()
        path = path or get_file_name(view)
        if path:
            save_view(view)
            thread = TfsRunnerThread(path, TfsManager().checkin)
            thread.start()
            ThreadProgress(view, thread, "Checkin: %s..." % path, "Checkin success: %s" % path)
class TfsFilesCheckinCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        paths = (files or []) + (dirs or [])
        if paths:
            TfsCheckinCommand(self.window).run(paths[0])
class TfsHistoryCommand(sublime_plugin.WindowCommand):
    def run(self, path=None):
        view = self.window.active_view()
        path = path or get_file_name(view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().history)
            thread.start()
            ThreadProgress(view, thread, "History: %s..." % path, "History success: %s" % path)
class TfsFilesHistoryCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        paths = (files or []) + (dirs or [])
        if paths:
            TfsHistoryCommand(self.window).run(paths[0])
class TfsAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if path:
            thread = TfsRunnerThread(path, TfsManager().add)
            thread.start()
            ThreadProgress(self.view, thread, "Adding: %s..." % path, "Added success: %s" % path)
class TfsGetLatestCommand(sublime_plugin.WindowCommand):
    def run(self, path=None):
        view = self.window.active_view()
        path = path or get_file_name(view)
        if path:
            save_view(view)
            thread = TfsRunnerThread(path, TfsManager().get_latest)
            thread.start()
            ThreadProgress(view, thread, "Getting: %s..." % path, "Get latest success: %s" % path)
class TfsFilesGetLatestCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        paths = (files or []) + (dirs or [])
        if paths:
            TfsGetLatestCommand(self.window).run(paths[0])
class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_file_name(self.view)
        if path:
            save_view(self.view)
            thread = TfsRunnerThread(path, TfsManager().difference)
            thread.start()
            ThreadProgress(self.view, thread, "Comparing...", "Comparing success: %s" % path)
class TfsDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_file_name(self.view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().delete)
            thread.start()
            ThreadProgress(self.view, thread, "Deleting...", "Delete success: %s" % path)
class TfsShelveCommand(sublime_plugin.WindowCommand):
    def run(self, path = None):
        view = self.window.active_view()
        path = path or get_file_name(view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().shelve)
            thread.start()
            ThreadProgress(view, thread, "Shelving...")
class TfsFilesShelveCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        paths = (files or []) + (dirs or [])
        if paths:
            TfsShelveCommand(self.window).run(paths[0])
class TfsStatusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_file_name(self.view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().status)
            thread.start()
            ThreadProgress(self.view, thread, "Getting status...")
class TfsAnnotateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_file_name(self.view)
        if path:
            thread = TfsRunnerThread(path, TfsManager().annotate)
            thread.start()
            ThreadProgress(self.view, thread, "Annotating...", "Annotate done")
class TfsMoveCommand(sublime_plugin.WindowCommand):
    # ------------------------------
    current_name = None
    new_name = None
    # ------------------------------
    def run(self, path = None):
        view = self.window.active_view()
        self.current_name = path or get_file_name(view)
        self.window.show_input_panel('New name', self.current_name, self.__on_done, None, None)
    # ------------------------------
    def __on_done(self, new_name):
        self.new_name = new_name
        TfsManager().move(self.current_name, self.new_name)
# ------------------------------------------------------------
class TfsEventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if not hasattr(self, 'manager'):
            self.manager = TfsManager()

        if self.manager.auto_checkout_enabled:
            path = view.file_name()
            if path:
                if is_readonly(path):
                    thread = TfsRunnerThread(path, self.manager.auto_checkout)
                    thread.start()
                    ThreadProgress(view, thread, "Checkout...", "Checkout success: %s" % path)
                    thread.join(self.manager.auto_checkout_timeout) #5 seconds by default, or defined in sublime-settings file
                    if thread.isAlive():
                        sublime.set_timeout(lambda: "Checkout failed. Too long operation")
# ------------------------------------------------------------
class TfsCheckoutOpenFilesCommand(sublime_plugin.WindowCommand):
    """
    Checkout all opened files
    """
    def run(self):
        for v in self.window.views():
            command = TfsCheckoutCommand(self.window)
            command.run(view = v)
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
def plugin_loaded():
    global credentials
    credentials = TfsCredentials()
# ------------------------------------------------------------
