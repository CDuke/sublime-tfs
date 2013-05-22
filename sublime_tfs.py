import sublime, sublime_plugin, re
import threading
import locale
import shlex
import subprocess
import os
import stat
import sys

def is_python_3_version():
    return sys.hexversion > 0x03000000

def get_unicode_filename(view):
    file_name = view.file_name() if is_python_3_version() else unicode(view.file_name())
    return file_name.encode(locale.getpreferredencoding()) if not file_name is None else None;

class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")
        self.tfpt_path = settings.get("tfpt_path")
        self.auto_checkout_enabled = settings.get("auto_checkout_enabled", True)
        self.cwd = os.path.expandvars('%HOMEDRIVE%\\')

    def is_under_tfs(self, path):
        return self.status(path)

    def checkout(self, path):
        if self.auto_checkout_enabled or sublime.ok_cancel_dialog("Checkout " + path + "?"):
            return self.run_command("checkout", path)
        else:
            return (False, "Checkout is cancelled by user!")

    def checkin(self, path):
        return self.run_command("checkin", path, True)

    def undo(self, path):
        return self.run_command("undo", path)

    def history(self, path):
        return self.run_command("history", path, True)

    def add(self, path):
        return self.run_command("add", path)

    def get_latest(self, path):
        return self.run_command("get", path)

    def difference(self, path):
        return self.run_command("difference", path, True)

    def delete(self, path):
        return self.run_command("delete", path)

    def status(self, path):
        return self.run_command("status", path)

    def annotate(self, path):
        return self.run_command("annotate", path, True, True)

    def auto_checkout(self, path):
        if self.status(path)[0]:
            return self.checkout(path)
        else:
            return (False, "")

    def run_command(self, command, path, is_graph = False, is_tfpt = False):
        commands = [self.tfpt_path if is_tfpt else self.tf_path, command, path]
        if (is_graph):
            p = subprocess.Popen(commands, cwd=self.cwd)
        else:
            p = self.launch_Without_Console(commands)
        (out, err) = p.communicate()
        if p.returncode != 0:
            return (False, err if not err is None else "Unknown error")
        else:
            return (True, out)

    def launch_Without_Console(self, command):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=self.cwd, startupinfo=startupinfo)

class TfsRunnerThread(threading.Thread):
    """docstring for ClearLogTread"""
    def __init__(self, path, method):
        super(TfsRunnerThread, self).__init__()
        self.method = method
        self.m_path = path
        self.success = False
        self.message = ""

    def run(self):
        (self.success, self.message) = self.method(self.m_path)

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
        if not self.thread.is_alive():
            self.view.erase_status('tfs')
            if not self.thread.success:
                sublime.status_message(self.thread.message)
                return
            sublime.status_message(self.success_message if not self.success_message is None else self.thread.message)
            return

        before = i % self.size
        after = (self.size - 1) - before
        self.view.set_status('tfs', '%s [%s=%s]' % (self.message, ' ' * before, ' ' * after))
        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend
        sublime.set_timeout(lambda: self.run(i), 100)

class TfsCheckoutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkout)
            thread.start()
            ThreadProgress(self.view, thread, "Checkout...", "Checkout success: %s" % path)

class TfsUndoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.undo)
            thread.start()
            ThreadProgress(self.view, thread, "Undo...", "Undo success: %s" % path)

class TfsCheckinCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            if (not isReadonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkin)
            thread.start()
            ThreadProgress(self.view, thread, "Checkin...", "Checkin success: %s" % path)

class TfsHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.history)
            thread.start()
            ThreadProgress(self.view, thread, "History...", "History success: %s" % path)

class TfsAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.add)
            thread.start()
            ThreadProgress(self.view, thread, "Adding...", "Added success: %s" % path)

class TfsGetLatestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            if (not isReadonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting...", "Get latest success: %s" % path)

class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            if (not isReadonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.difference)
            thread.start()
            ThreadProgress(self.view, thread, "Comparing...", "Comparing success: %s" % path)

class TfsDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.delete)
            thread.start()
            ThreadProgress(self.view, thread, "Deleting...", "Delete success: %s" % path)

class TfsStatusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.status)
            thread.start()
            ThreadProgress(self.view, thread, "Getting status...")

class TfsAnnotateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = get_unicode_filename(self.view)
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.annotate)
            thread.start()
            ThreadProgress(self.view, thread, "Annotating...")

class TfsEventListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        if not manager.auto_checkout_enabled:
            return
        path = get_unicode_filename(view)
        if not (path is None):
            manager = TfsManager()
            if isReadonly(path):
                thread = TfsRunnerThread(path, manager.auto_checkout)
                thread.start()
                ThreadProgress(view, thread, "Checkout...", "Checkout success: %s" % path)

def isReadonly(p_path):
    try:
        fileAttrs = os.stat(p_path)
        fileAtt = fileAttrs[0]
        return not fileAtt & stat.S_IWRITE
    except WindowsError:
        pass
