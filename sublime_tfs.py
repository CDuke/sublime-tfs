﻿import sublime
import sublime_plugin
import threading
import locale
import subprocess
import os
import stat
import sys

def is_python_3_version():
    return sys.hexversion > 0x03000000

def get_path(view):
    return view.file_name() if is_python_3_version() else view.file_name().encode(locale.getpreferredencoding())

def encode_string(s, default=None):
    try:
        return s.encode(locale.getpreferredencoding()) if not s is None else default
    except UnicodeEncodeError:
        return s if not s is None else default

def decode_string(s, default=None):
    try:
        return s.decode(locale.getpreferredencoding()) if not s is None else default
    except UnicodeDecodeError:
        return s if not s is None else default

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
            return self.run_command(["checkout"], path)
        else:
            return (False, "Checkout is cancelled by user!")

    def checkin(self, path):
        return self.run_command(["checkin"], path, True)

    def undo(self, path):
        return self.run_command(["undo"], path)

    def history(self, path):
        return self.run_command(["history"], path, True)

    def add(self, path):
        return self.run_command(["add"], path)

    def get_latest(self, path):
        return self.run_command(["get"], path)

    def dir_get_latest(self, path):
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
            commands = [self.tfpt_path if is_tfpt else self.tf_path] + command + [path]
            if (is_python_3_version()):
                return self.run_command_inner(commands, is_graph, decode_string)
            else:
                commands = map(lambda s: encode_string(s, s), commands)
                return self.run_command_inner(commands, is_graph, encode_string)
        except Exception:
            print("commands: %s" % commands)
            print("is_graph: %s" % is_graph)
            raise

    def run_command_inner(self, commands, is_graph, converter):
        if (is_graph):
            p = subprocess.Popen(commands, cwd=self.cwd)
        else:
            p = self.launch_without_console(commands)
        (out, err) = p.communicate()
        return (True, converter(out, None)) if (p.returncode == 0) else (False, converter(err, "Unknown error"))

    def launch_without_console(self, command):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=self.cwd, startupinfo=startupinfo)

class TfsRunnerThread(threading.Thread):
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

class TfsDirGetLatestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        if not (path is None):
            path = os.path.dirname(path)
            manager = TfsManager()
            thread = TfsRunnerThread(path, manager.dir_get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting dir: %s..." % path, "Directory get latest success: %s" % path)

class TfsDirsGetLatestCommand(sublime_plugin.TextCommand):
    def is_visible(self, dirs):
        return (dirs != None) and (len(dirs) > 0) and all(os.path.isdir(item) for item in dirs)

    def run(self, edit, dirs):
        path = dirs[0] # currently do GLV for first selected directory only
        manager = TfsManager()
        thread = TfsRunnerThread(path, manager.dir_get_latest)
        thread.start()
        ThreadProgress(self.view, thread, "Getting dir: %s..." % path, "Directory get latest success: %s" % path)

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
    def on_activated(self, view):
        if not hasattr(self, 'manager'):
            self.manager = TfsManager()

    def on_pre_save(self, view):
        if not self.manager.auto_checkout_enabled:
            return
        path = view.file_name()
        if not (path is None):
            if is_readonly(path):
                thread = TfsRunnerThread(path, self.manager.auto_checkout)
                thread.start()
                ThreadProgress(view, thread, "Checkout...", "Checkout success: %s" % path)
                thread.join(5) #5 seconds. It's enough for checkout.
                if thread.isAlive():
                    sublime.set_timeout(lambda: "Checkout failed. Too long operation")

def is_readonly(path):
    try:
        return not os.stat(path)[0] & stat.S_IWRITE
    except WindowsError:
        pass
