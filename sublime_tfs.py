import sublime, sublime_plugin, re
import threading
import shlex
import subprocess

class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")

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
            p = subprocess.Popen(commands, cwd="C:/")
        else:
            p = self.launch_Without_Console(commands)
        (out, err) = p.communicate()
        if not (err is None or err == ""):
            return (False, err)
        else:
            return (True, "")

    def launch_Without_Console(self, command):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd="C:/", startupinfo=startupinfo)

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
    def __init__(self, view, thread, message, success_message):
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
            if hasattr(self.thread, 'success') and not self.thread.success:
                sublime.status_message(self.thread.message)
                return
            sublime.status_message(self.success_message)
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
            ThreadProgress(self.view, thread, "Checkout...", "Chekout sucess: %s" % path)

class TfsUndoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.undo)
            thread.start()
            ThreadProgress(self.view, thread, "Undo...", "Undo sucess: %s" % path)

class TfsCheckinCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.checkin)
            thread.start()
            ThreadProgress(self.view, thread, "Checkin...", "Checkin sucess: %s" % path)

class TfsHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.history)
            thread.start()
            ThreadProgress(self.view, thread, "History...", "History sucess: %s" % path)

class TfsAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.add)
            thread.start()
            ThreadProgress(self.view, thread, "Adding...", "Added sucess: %s" % path)

class TfsGetLatestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting...", "Get latest sucess: %s" % path)

class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.difference)
            thread.start()
            ThreadProgress(self.view, thread, "Comparing...", "Comparing sucess: %s" % path)

class TfsDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.delete)
            thread.start()
            ThreadProgress(self.view, thread, "Deleting...", "Delete sucess: %s" % path)

class TfsStatusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.delete)
            thread.start()
            ThreadProgress(self.view, thread, "Get status...", "Got status sucess: %s" % path)


