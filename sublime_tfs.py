import sublime, sublime_plugin, re
import threading
import locale
import shlex
import subprocess
import os
import stat

def get_unicode_filename(view):
    return unicode(view.file_name()).encode(locale.getpreferredencoding());

class TfsManager(object):
    def __init__(self):
        self.name = 'sublime_tfs'
        settings = sublime.load_settings('sublime_tfs.sublime-settings')
        self.tf_path = settings.get("tf_path")
        self.tfpt_path = settings.get("tfpt_path")
        self.auto_checkout_enabled = settings.get("auto_checkout_enabled", True)
        self.cwd = os.path.expandvars('%HOMEDRIVE%\\')

    def is_under_tfs(self, p_path):
        return self.status(p_path)

    def checkout(self, p_path):
        if self.auto_checkout_enabled or sublime.ok_cancel_dialog("Checkout " + p_path + "?"):
            return self.run_command("checkout", p_path)
        else:
            return (False, "Checkout is cancelled by user!")

    def checkin(self, p_path):
        return self.run_command("checkin", p_path, True)

    def undo(self, p_path):
        return self.run_command("undo", p_path)

    def history(self, p_path):
        return self.run_command("history", p_path, True)

    def add(self, p_path):
        return self.run_command("add", p_path)

    def get_latest(self, p_path):
        return self.run_command("get", p_path)

    def difference(self, p_path):
        return self.run_command("difference", p_path, True)

    def delete(self, p_path):
        return self.run_command("delete", p_path)

    def status(self, p_path):
        return self.run_command("status", p_path)

    def annotate(self, p_path):
        return self.run_command("annotate", p_path, True, True)

    def auto_checkout(self, p_path):
        if self.status(p_path)[0]:
            return self.checkout(p_path)
        else:
            return (False, "")

    def run_command(self, command, p_path, is_graph = False, is_tfpt = False):
        commands = [self.tfpt_path if is_tfpt else self.tf_path, command, p_path]
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
    def __init__(self, p_path, method):
        super(TfsRunnerThread, self).__init__()
        self.method = method
        self.m_path = p_path
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
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.checkout)
            thread.start()
            ThreadProgress(self.view, thread, "Checkout...", "Checkout success: %s" % v_path)

class TfsUndoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.undo)
            thread.start()
            ThreadProgress(self.view, thread, "Undo...", "Undo success: %s" % v_path)

class TfsCheckinCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            if (not isReadonly(v_path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.checkin)
            thread.start()
            ThreadProgress(self.view, thread, "Checkin...", "Checkin success: %s" % v_path)

class TfsHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.history)
            thread.start()
            ThreadProgress(self.view, thread, "History...", "History success: %s" % v_path)

class TfsAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.add)
            thread.start()
            ThreadProgress(self.view, thread, "Adding...", "Added success: %s" % v_path)

class TfsGetLatestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            if (not isReadonly(v_path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.get_latest)
            thread.start()
            ThreadProgress(self.view, thread, "Getting...", "Get latest success: %s" % v_path)

class TfsDifferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            if (not isReadonly(v_path)):
                self.view.run_command('save')
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.difference)
            thread.start()
            ThreadProgress(self.view, thread, "Comparing...", "Comparing success: %s" % v_path)

class TfsDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.delete)
            thread.start()
            ThreadProgress(self.view, thread, "Deleting...", "Delete success: %s" % v_path)

class TfsStatusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.status)
            thread.start()
            ThreadProgress(self.view, thread, "Getting status...")

class TfsAnnotateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v_path = get_unicode_filename(self.view)
        if not (v_path is None):
            manager = TfsManager()
            thread = TfsRunnerThread(v_path, manager.annotate)
            thread.start()
            ThreadProgress(self.view, thread, "Annotating...")

class TfsEventListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        v_path = get_unicode_filename(view)
        if not (v_path is None):
            manager = TfsManager()
            if isReadonly(v_path):
                if manager.auto_checkout_enabled:
                    thread = TfsRunnerThread(v_path, manager.auto_checkout)
                    thread.start()
                    ThreadProgress(view, thread, "Checkout...", "Checkout success: %s" % v_path)

def isReadonly(p_path):
    try:
        fileAttrs = os.stat(p_path)
        fileAtt = fileAttrs[0]
        return not fileAtt & stat.S_IWRITE
    except WindowsError:
        pass
