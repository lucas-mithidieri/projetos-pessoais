from os import path, stat
from PIL import Image, ImageTk
from code import interact
from queue import Queue
from threading import Event, Thread
from tkinter import Button, Frame, Menu, PanedWindow, Scrollbar, Text, Tk
from tkinter import filedialog, messagebox
from syntax_coloring import apply_syntax_coloring
import regex as re
import numpy as np
import logging
import asyncio
import time
import sys
import pdb

BASE_DIR = path.dirname(__file__)
CURRENT_FILE = ''
MODIFIED_TIME = -1
TAB_SIZE = 4
MENU_FONT_SIZE = 11

class EmptyWriter:
    def write(self, *args):
        pass
    def flush(self, *args):
        pass

class App(Frame):
    def __init__(self, root:Tk, locals):
        Frame.__init__(self, root)
        self._locals = locals
        self.toolbar_icons = []
        self.appname = "PYIDE"
        self.root = root
        self.terminal_backspace_limit = None
        self.should_stop_execution = False
        self.is_debugging = False
        self.silence_exception = False
        self.configure_window()
        self.load_menus()
        self.load_toolbar()
        self.load_editor()
        self.load_terminal()
        self.bind_events()
        self.reroute_terminal()
        self.configure_logger()
        self.current_execution = 1

    def new_tools_button(self, icon_filename='play.png', command=None):
        img = Image.open(f"{BASE_DIR}\\{icon_filename}")
        self.toolbar_icons.append(ImageTk.PhotoImage(img))
        button = Button(self.toolbar_tools, image=self.toolbar_icons[-1], command=command) #, bd=1, relief='raised', command=run_all)
        button.pack(side='left', padx=2, pady=2)
        return button

    def stop_execution(self, *args):
        
        if self.is_debugging:
            self.debug_interrupt()
            return 'break'
        
        # Define o sinalizador para interromper a execução
        self.should_stop_execution = True

    def load_toolbar(self):
        self.toolbar = Frame(self.root, bd=1, relief='raised')
        self.toolbar_tools = Frame(self.toolbar, bd=0, relief='flat')
        
        self.toolbar.pack()#side='top', fill='x')
        self.toolbar_tools.pack()

        # Buttons ####################################################
        self.run_all_button = self.new_tools_button(icon_filename='play.png', command=self.run_all)
        
        cmd = lambda event=None: self.stop_execution(event)
        self.stop_execution_button = self.new_tools_button(icon_filename='stop.png', command=cmd)

        self.inspect_button = self.new_tools_button(icon_filename='inspect.png')

        self.debug_button = self.new_tools_button(icon_filename='debug_.png', command=lambda:self.run_all(True))

        self.next_button = self.new_tools_button(icon_filename='next.png', command=self.debug_next_line)

        self.continue_button = self.new_tools_button(icon_filename='continue.png', command=self.debug_continue)
        
        self.continue_button['state'] = 'disabled'
        self.next_button['state'] = 'disabled'

    def load_menus(self):
        menu_font = ("", MENU_FONT_SIZE)

        # Create a menu bars
        menubar = Menu(root)
        file_menu = Menu(menubar, tearoff=0)
        edit_menu = Menu(menubar, tearoff=0)

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        # menubar.add_cascade(label="Settings", menu=tools_menu)

        file_menu.add_command(label="New", command=self.new_file, font=menu_font)
        file_menu.add_command(label="Open", command=self.open_file, font=menu_font)
        file_menu.add_command(label="Save", font=menu_font)#, command=open_file)
        file_menu.add_command(label="Save-as", font=menu_font)#, command=open_file)
        edit_menu.add_command(label="Undo", font=menu_font)#, command=open_file)
        edit_menu.add_command(label="Redo", font=menu_font)#, command=open_file)

        self.root.config(menu=menubar)


    def load_editor(self):
        # PanedWindow
        paned_window = PanedWindow(self.root, orient='vertical')
        self.editor_paned_window = paned_window

        # Frame no primeiro painel
        group_frame = Frame(paned_window)
        self.editor_group_frame = group_frame
        paned_window.add(self.editor_group_frame)
        
        editor = Text(group_frame, 
                      undo=True,
                      background='#0D0D0D', 
                      font=("Consolas", 12),
                      foreground="white", 
                      insertbackground="white", 
                      padx=14, 
                      pady=10, 
                      tabs=(32,),
                      wrap='none')
        editor.config(spacing1=6)
        editor.pack(side='left')
        self.editor = editor

        # Scrollbar
        scrollbar = Scrollbar(group_frame, command=editor.yview)
        scrollbar.pack(side='right', fill='y')
        editor.config(yscrollcommand=scrollbar.set)

        # Apply syntax coloring
        apply_syntax_coloring(self.editor)

    def load_terminal(self):
        group_frame = Frame(self.editor_paned_window)
        self.terminal_group_frame = group_frame
        self.editor_paned_window.add(self.terminal_group_frame)
        
        self.editor_paned_window.grid_rowconfigure(0, weight=0)
        self.editor_paned_window.grid_columnconfigure(0, weight=0)
        self.editor_paned_window.paneconfig(self.editor_group_frame, height = 500, sticky='ewsn')
        self.editor_paned_window.pack(expand=True, fill='y')

        # Terminal
        terminal = Text(group_frame, 
                        background='#0D0D0D', 
                        font=("Consolas", 12), 
                        foreground="white",
                        insertbackground="white", 
                        padx=14, 
                        pady=10, 
                        tabs=(32,),
                        wrap='word')
        #terminal.grid(row=0, column=0, sticky='nsew')#tk.N + tk.S + tk.E + tk.W)
        terminal.pack(side='left')#, expand=True, fill='both')
        terminal.mark_set("input_start", "end-1c")
        terminal.mark_gravity("input_start", "left")
        self.terminal = terminal

        # Scrollbar
        scrollbar = Scrollbar(group_frame, command=terminal.yview)
        scrollbar.pack(side='right', fill='y')
        terminal.config(yscrollcommand=scrollbar.set)

    def reroute_terminal(self):
        # Init
        # self.parent = self.root
        self.exit_callback = self.root.destroy
        self.destroyed = False

        # Salva as referências para os objetos originais de stdin, stdout e stderr
        self.real_std_in_out = (sys.stdin, sys.stdout, sys.stderr)

        # Redireciona stdin, stdout e stderr para a instância
        sys.stdout = self
        sys.stderr = self
        sys.stdin = self

        # Substituir a função padrão de input do PDB
        global custom_pdb
        self.custom_pdb = pdb.Pdb(stdout=self, stdin=self)
        #self.custom_pdb.use_rawinput = 0
        custom_pdb = self.custom_pdb

        # Fila para armazenar as entradas do usuário
        self.stdin_buffer = Queue()

        # Inicia uma thread para executar o console interativo
        self.terminalThread = Thread(target=lambda: self.run_terminal(self._locals))
        self.terminalThread.start()
        
    def run_terminal(self, _locals):
        try:
            # Inicia o console interativo usando a função interact do módulo code
            interact(local=_locals)
        except SystemExit:
            # Trata a exceção SystemExit, chamando o callback de saída se necessário
            if not self.destroyed:
                self.after(0, self.exit_callback)

    def enter(self, event):
        # Obtém a linha de entrada do usuário e a coloca na fila de entradas
        input_line = self.terminal.get("input_start", "end")
        
        if input_line.isspace():
            return 'break'
        
        self.terminal.mark_set("input_start", "end-1c")
        self.terminal.mark_gravity("input_start", "left")
        self.stdin_buffer.put(input_line)
        self.current_execution += 1

    def write(self, string):
        # Gera uma exceção de KeyboardInterrupt para interromper a execução
        if self.should_stop_execution:
            self.should_stop_execution = False
            print()
            raise KeyboardInterrupt

        filtered_string = ''
        if self.is_debugging:        
            try:
                # se ele conseguir, significa que um arquivo externo está sendo
                # depurado, e uma aba precisa ser aberta.
                current_file = self.custom_pdb.curframe.f_code.co_filename
                s = current_file
                if current_file == '<string>':
                    # retornos no atual e no externo
                    s = 'RETURN'
                    
                    ###############################################################
                    # Limpe o destaque da linha
                    self.editor.tag_remove("highlight", "1.0", "end")

                    # Obtem a linha atual
                    line = self.custom_pdb.curframe.f_lineno

                    # Adicione destaque à linha atual
                    self.editor.tag_add("highlight", f"{line - 2}.0", f"{line - 2}.end")
                    self.editor.tag_config("highlight", background="#414141")

                    # Atualize a interface gráfica para garantir a renderização
                    self.root.update()
                    ###############################################################

                elif current_file == '<console>':
                    s = 'CONSOLE'
                elif path.exists(current_file):
                    s = 'EXTERNAL_FILE'
                else:
                    s = 'OTHER'
                #s = f'A{external_file}B'#f_lineno
            except:
                # significa que estamos no arquivo atual
                s = 'CURRENT'
                filtered_string = string
                pass
        
        # preciso mudar essa lógica abaixo pra que os unbinds
        # sejam sempre executados
        if self.silence_exception:
            # self.terminal.insert('end', '--Interrupt--')
            self.silence_exception = False

            # resetar os bindings
            # rebind no stdout de Pdb
            self.custom_pdb.stdout = self

            self.editor.bind('<Control-Return>', self.run_all)
            self.root.unbind('<Escape>')
            self.run_all_button['state'] = 'normal'
            self.inspect_button['state'] = 'normal'
            self.stop_execution_button['state'] = 'disabled'
            self.continue_button['state'] = 'disabled'
            self.next_button['state'] = 'disabled'
            self.debug_button['state'] = 'normal'

            return 'break'
        
        if not self.is_debugging:
            # Escreve a saída do console na interface gráfica
            filtered_string = string.replace(">>>", f"\nIn [{self.current_execution}]:")
        
        self.terminal.insert('end', filtered_string)
        self.terminal.mark_set("input_start", "end-1c")
        self.terminal.see('end')
        self.terminal_backspace_limit = self.terminal.index('end-1c')

        # resetar os bindings
        if string == '>>> ':
            # rebind no stdout de Pdb
            self.custom_pdb.stdout = self

            self.editor.bind('<Control-Return>', self.run_all)
            self.root.unbind('<Escape>')
            self.run_all_button['state'] = 'normal'
            self.inspect_button['state'] = 'normal'
            self.stop_execution_button['state'] = 'disabled'
            self.continue_button['state'] = 'disabled'
            self.next_button['state'] = 'disabled'
            self.debug_button['state'] = 'normal'

        # se o arquivo é externo e nao estou usando
        # step into, continua até o fim
        if self.is_debugging and string == '--Return--':
            self.debug_continue()
            # Desativa o stdout de pdb
            self.custom_pdb.stdout = EmptyWriter()
            return 'break'

    def readline(self):
        # Lê uma linha da fila de entradas do usuário
        line = self.stdin_buffer.get()
        return line

    def flush(self):
        # Método obrigatório, mas não utilizado neste contexto
        pass

    def destroy(self):
        # Adiciona um comando de saída na fila para encerrar o console interativo
        self.stdin_buffer.put("\n\nexit()\n")
        self.destroyed = True

        # Restaura os objetos originais de stdin, stdout e stderr
        sys.stdin, sys.stdout, sys.stderr = self.real_std_in_out
        super().destroy()

    def configure_window(self):
        self.root.title(f"{self.appname} - Untitled")

        # Center the main window on the screen
        window_width = 1024
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{screen_height - 50}+{x}+{0}")

    def configure_logger(self):
        pass
        # logging.basicConfig(level=logging.DEBUG)

    def open_file(self, *args):
        global CURRENT_FILE, MODIFIED_TIME

        path = CURRENT_FILE

        reload_file = False

        if type(args[0]) == bool:
            reload_file = args[0]

        if not reload_file:
            path = filedialog.askopenfilename(filetypes=(("Python","*.py"),
                                                         ("All files","*.*")))
        try:
            # Are o arquivo
            with open(path, 'r') as file:
                lines = file.read()

            # atualiza var global
            CURRENT_FILE = path
            MODIFIED_TIME = stat(CURRENT_FILE).st_mtime

            editor = self.editor

            # Limpa a barra de índices e
            # readiciona a tag de justify
            # line_index_bar.delete('1.0', END)
            # line_index_bar.tag_add("right", 1.0, "end")
            # line_index_bar.insert(tk.INSERT,f"{1}", "right")
            
            # Limpa o editor e adiciona o conteúdo
            editor.delete('1.0', 'end')
            editor.insert('1.0', lines)
            editor.mark_set('insert', '1.0')
            editor.focus_set()

            # Limpar a pilha de undo
            editor.edit_reset()

            # atualiza o titulo do app
            self.root.title(f"{self.appname} - " + path)  
        except:
            pass
            
        return "break"

    def new_file(self, *args):
        global CURRENT_FILE, MODIFIED_TIME
        MODIFIED_TIME = -1
        self.editor.delete('1.0', 'end')
        root.title(f"{self.appname} - Untitled")
        return 'break'

    def editor_tab_event_handler(self, *args):
        editor = self.editor
        selected_code = editor.get("sel.first", "sel.last")

        if selected_code == '':
            # Garante que o texto da 1a linha seja toda a linha
            start_index = editor.index("insert").split('.')[0] 
            # selected_code = editor.get(start_index + ".0", start_index + ".end")

            # Insert the 4 spaces
            editor.insert(start_index + ".0", " " * TAB_SIZE)
            return "break"
        else:
            # Garante que o texto da 1a linha seja toda a linha
            start_index = editor.index("sel.first").split('.')[0] + ".0"
            selected_code = editor.get(start_index, "sel.last")

        tabs = f'\n{" "*4}'
        new_str = " "*4 + selected_code.replace('\n', tabs)
        
        # previne tabs adicionais no Ctrl+A
        if selected_code[-1] == '\n':
            new_str = new_str[:-5]

        # Obtém a posição inicial e final da seleção
        # start_index = editor.index("sel.first")
        end_index = editor.index("sel.last")

        # Substitui o texto selecionado
        editor.delete(start_index, end_index)
        editor.insert(start_index, new_str)

        # Seleciona o texto recém substituído
        # Obtém a posição do final do texto após a inserção
        end_index = editor.index("insert")
        editor.tag_add("sel", start_index, end_index)

        # Prevent the default Tab behaviour call
        return "break"        
    
    def editor_shift_tab_event_handler(self, *args):
        editor = self.editor

        selected_code = editor.get("sel.first", "sel.last")
    
        is_empty_selection = selected_code == ''

        if is_empty_selection:
            # Obtém a posição do cursor no formato "linha.coluna"
            cursor_position = editor.index('insert')
            
            # Obtém o início da linha atual (linha.atividade_inicial)
            start_index = cursor_position.split('.')[0] + ".0"

            # Obtém o final da linha atual (linha.atividade_final)
            end_index = cursor_position.split('.')[0] + ".end"

            # Obtém o texto da linha atual
            selected_code = editor.get(start_index, end_index)

            # Garante que não está vazio o editor
            if selected_code == '':
                return 'break'
        else:
            # Garante que o texto da 1a linha seja toda a linha
            start_index = editor.index("sel.first").split('.')[0] + ".0"
            selected_code = editor.get(start_index, "sel.last")

        # Verifica se o primeiro caractere de selected_code 
        # não é uma quebra de linha.
        missing_new_line_char = selected_code[0] != '\n'

        # Adiciona uma quebra de linha no início de selected_code
        # se estiver faltando.
        if  missing_new_line_char:
            selected_code = '\n' + selected_code

        # Substitui todas as ocorrências de tabs 
        # por uma quebra de linha em selected_code.
        tabs = f'\n{" "*4}'
        new_str = selected_code.replace(tabs, '\n')
        
        # Remove a quebra de linha no final se houver
        if selected_code[-1] == '\n':
            new_str = new_str[:-1]    

        # Remove a primeira quebra de linha 
        # se ela tiver sido adicionada anteriormente.
        if missing_new_line_char:
            new_str = new_str[1:]

        # Obtém a posição inicial e final da seleção
        if not is_empty_selection:
            # start_index = editor.index("sel.first")
            end_index = editor.index("sel.last")

        # Substitui o texto selecionado
        editor.delete(start_index, end_index)
        editor.insert(start_index, new_str)

        # Seleciona o texto recém substituído
        if not is_empty_selection:
            # Obtém a posição do final do texto após a inserção
            end_index = end_index.split('.')[0] + ".end"
            editor.tag_add("sel", start_index, end_index)
            # Move o cursor para o fim do grupo
            editor.mark_set("insert", end_index)

        return 'break'

    def editor_return_event_handler(self, *args):
        """
        Handles the event when a user adds a new line.

        Parameters:
            event (tkinter.Event): The event triggered by the user.

        Returns:
            str: "break" to prevent the default behavior.
        """
        event = args[0]
        text_widget = event.widget
        current_line = text_widget.get("insert linestart", "insert")
        match = re.match(r'^(\s+)', current_line)
        whitespace = match.group(0) if match else ""
        text_widget.insert("insert", f"\n{whitespace}")

        return "break"

    def editor_backspace_event_handler(self, *args):
        event = args[0]
        text_widget = event.widget
        current_line = text_widget.get("insert linestart", "insert")
            
        if current_line == '' or current_line[-1] not in ['\n','\t',' ']:
            # default behaviour
            return
        
        # global identation size
        pattern = r'(\s{1,' + str(TAB_SIZE) + '})'

        # search for 
        matches = re.findall(pattern, current_line)
        if matches:
            last_match = matches[-1]
            text_widget.delete(f"insert-{len(last_match)}c", "insert")
            return 'break'
    
    def root_focusin_event_handler(self, *args):    
        global CURRENT_FILE, MODIFIED_TIME
        
        #print('catching', np.random.randint(99))

        if CURRENT_FILE != '':
            modification_time = stat(CURRENT_FILE).st_mtime
            
            if modification_time > MODIFIED_TIME:
                # Desvincular temporariamente o evento <FocusIn>
                self.root.unbind('<FocusIn>')

                msg = 'This file has been modified outside PYIDE.\nDo you want to reload it?'
                res = messagebox.askyesno("Alerta", msg, icon='warning')

                if res:
                    # reload the file
                    self.open_file(True)
                    # return 'break'
                else:
                    # update MODIFIED_TIME 
                    MODIFIED_TIME = modification_time

                # Vincular novamente o evento <FocusIn> após o fechamento do messagebox
                self.root.bind('<FocusIn>', self.root_focusin_event_handler)
        
        return 'break'

    def terminal_backspace_event_handler(self, *args):
        cursor = self.terminal.index('insert')
        limit = self.terminal_backspace_limit

        rows_statement = cursor.split('.')[0] == limit.split('.')[0]
        cols_statement = int(cursor.split('.')[1]) > int(limit.split('.')[1])

        if cols_statement and rows_statement:
            return
        
        return 'break'

    def run_all(self, *args):
        # unbind events
        self.editor.unbind('<Control-Return>')
        self.root.bind('<Escape>', self.stop_execution)
        self.run_all_button['state'] = 'disabled'
        self.inspect_button['state'] = 'disabled'
        self.stop_execution_button['state'] = 'normal'
        
        selected_code = self.editor.get("1.0", "end-1c")
        escaped_code = selected_code.replace("'", "\\'\\'\\'")
        escaped_code = escaped_code.replace('"', '\\"\\"\\"')

        # start debugging session
        if len(args) and args[0]:
            self.continue_button['state'] = 'normal'
            self.next_button['state'] = 'normal'
            self.debug_button['state'] = 'disabled'

            # print('Debugging')
            self.is_debugging = True
            self.stdin_buffer.put(f"exec('''print()\ncustom_pdb.set_trace()\n{escaped_code}''', globals())")
            return 'break'

        self.stdin_buffer.put(f"exec('''print()\n{escaped_code}''', globals())")
        self.current_execution += 1
        return 'break'
    
    def debug_next_line(self, *args):
        self.stdin_buffer.put('n')

    def debug_continue(self, *args):
        self.is_debugging = False
        self.stdin_buffer.put('c')
        # increment exec
        self.current_execution += 1
        
    def debug_interrupt(self, *args):
        # envia o comando pra encerrar pdb
        self.stdin_buffer.put('q')
        # silencia a excessão gerada por 'quit'
        self.silence_exception = True
        self.is_debugging = False
        # increment exec
        self.current_execution += 1

    def terminal_key_event_handler(self, *args):
        cursor = self.terminal.index('insert')
        limit = self.terminal_backspace_limit
        cursor_at_same_line = cursor.split('.')[0] == limit.split('.')[0]
        if not cursor_at_same_line:
            # quero colocar o cursor do fim antes do break
            self.terminal.mark_set('insert', 'end-1c')
            return 'break'

    def bind_events(self):
        self.root.bind('<Control-n>', self.new_file)
        self.root.bind('<Control-o>', self.open_file)
        self.root.bind('<FocusIn>', self.root_focusin_event_handler)
        self.editor.bind("<Tab>", self.editor_tab_event_handler)
        self.editor.bind('<Shift-Tab>', self.editor_shift_tab_event_handler)
        self.editor.bind('<Return>', self.editor_return_event_handler)
        self.editor.bind('<BackSpace>', self.editor_backspace_event_handler)
        self.editor.bind('<Control-Return>', self.run_all)
        self.root.bind('<Escape>', self.stop_execution)
        self.terminal.bind('<Key>', self.terminal_key_event_handler)
        self.terminal.bind('<Return>', self.enter)
        self.terminal.bind('<BackSpace>', self.terminal_backspace_event_handler)
        


if __name__ == "__main__":
    root = Tk()
    app = App(root, locals=locals())
    root.mainloop()