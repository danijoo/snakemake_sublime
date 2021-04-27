import sublime
import sublime_plugin

import threading
import subprocess
import os

OUTPUT_PANEL_NAME = "snakemake"

class SnakemakeBuildCommand(sublime_plugin.WindowCommand):

    encoding = 'utf-8'
    panel = None
    panel_lock = threading.Lock()
    killed = False
    proc = None

    working_dir = None
    snakefile = "Snakefile"
    run_args = ""

    def run(self,  kill=False, wants_args=False):
        if kill:
            kill_run()
            return

        vars = self.window.extract_variables()
        if "file_path" in vars:
            self.working_dir = vars['file_path']

        # project arguments
        project_data = self.get_project_data()
        self.working_dir = project_data.get("working_dir", self.working_dir)
        self.snakefile = project_data.get("snakefile", self.snakefile)

        # Select rule
        if wants_args:
            self.window.show_input_panel(
                "Select rule:",
                self.run_args, self.on_args_select, None, None)
            return
        else:
            self.args = ""


        self.run_snakemake()

    def run_snakemake(self):
        cmd = []

        if self.run_args is not "":
            cmd += self.run_args.split()

        if not "--cores" in cmd and not "--jobs" in cmd and not "-j" in cmd:
            cmd = ["-j", "all"] + cmd
        if not "--snakefile" in cmd and not "-s" in cmd:
            cmd = ["-s", self.snakefile] + cmd

        cmd = ["snakemake"] + cmd

        with self.panel_lock:
            self.setup_panel()

        if self.working_dir is None:
            raise ValueError("No file opened and no working dir specified in project.")

        # run the command in a separate thread
        self.queue_write("[" + " ".join(cmd) + "]\n")
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.working_dir
        )
        threading.Thread(
            target=self.read_handle,
            args=(self.proc.stdout,),
        ).start()

    def on_args_select(self, run_args):
        self.run_args = run_args
        self.run_snakemake()

    def get_project_data(self):
        data = self.window.project_data()
        return data.get("snakemake", {})

    def kill_run(self):
        if self.proc:
            self.killed = True
            self.proc.terminate()
        return self.killed

    def setup_panel(self):
        self.panel = self.window.create_output_panel(OUTPUT_PANEL_NAME)

        settings = self.panel.settings()
        # settings.set(
        #     'result_file_regex',
        #     r'^File "([^"]+)" line (\d+) col (\d+)'
        # )
        # settings.set(
        #     'result_line_regex',
        #     r'^\s+line (\d+) col (\d+)'
        # )
        settings.set('word_wrap', True)
        settings.set('line_numbers', False)
        settings.set('gutter', False)
        settings.set('scroll_past_end', False)
        # settings.set('result_base_dir', working_dir)

        self.window.run_command('show_panel', {'panel': 'output.'+OUTPUT_PANEL_NAME})


    def read_handle(self, handle):
        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                # If exactly the requested number of bytes was
                # read, there may be more data, and the current
                # data may contain part of a multibyte char
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                # We pass out to a function to ensure the
                # timeout gets the value of out right now,
                # rather than a future (mutated) version
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''
            except (UnicodeDecodeError) as e:
                msg = 'Error decoding output using %s - %s'
                self.queue_write(msg  % (self.encoding, str(e)))
                break
            except (IOError):
                msg = 'Finished'
                self.queue_write('\n[%s]' % msg)
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 1)

    def do_write(self, text):
        with self.panel_lock:
            self.panel.run_command('append', {'characters': text, 'scroll_to_end': True})