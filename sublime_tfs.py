import sublime, sublime_plugin, re
import threading
import shlex
import subprocess
import os
import stat

class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")
        self.cwd = os.path.expandvars('%HOMEDRIVE%\\')

    def is_under_tfs(self, path):
        return self.status(path)

    def checkout(self, path):
        return self.run_command("checkout", path)

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

    def run_command(self, command, path, is_graph = False):
        commands = [self.tf_path, command, path]
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
        self.path = path
        self.success = False
        self.message = ""

    def run(self):
        (self.success, self.message) = self.method(self.path)

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
            if (not isReadonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkin)
            thread.start()
            ThreadProgress(self.view, thread, "Checkin...", "Checkin success: %s" % path)

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
            if (not isReadonly(path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting...", "Get latest success: %s" % path)

class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            if (not isReadonly(path)):
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

def isReadonly(path):
    fileAtt = os.stat(path)[0]
    return not fileAtt & stat.S_IWRITE
