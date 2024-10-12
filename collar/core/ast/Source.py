from abc import ABC, abstractmethod
import os,re
from jpype import JClass,JString
action_keys = [
    "-DES",
    "-CODE",
    "-MOD",
    "-DOC",
    "-QA",
    "-UNT",
    "-RUN"
]

class Source(ABC):
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = os.path.basename(self.file_path)
        self.short_file_name = os.path.splitext(self.file_name)[0]
        self.body = []
        self.changed = False
        self.build()

    @abstractmethod
    def build(self):
        pass
    @abstractmethod
    def unparse(self):
        pass
    @abstractmethod
    def get_extra_def(self):
        pass
    

class Decla(ABC):
    def __init__(self, decla, source,class_obj=None):
        self.class_obj = class_obj
        if class_obj:
            class_obj.body.append(self)
        self.decla = decla
        self.str_code = str(decla.toString())
        self.source = source
        self.body = []
        self.build()
        source.body.append(self)
    def build_name(self):
        if hasattr(self.decla, "getNameAsString"):
            self.name =  str(self.decla.getNameAsString().toString())
        else:
            self.name = ""
    def build_def_string(self):
         self.def_string = f"{self.design_doc_string}\n{str(self.decla.toString())}"
    
    def build_signature(self):
        self.signature = str(self.decla.toString())
    def build(self):
        self.build_name()
        self.build_signature()
        self.build_design_doc_string()
        self.build_def_string()
        pass
    @abstractmethod
    def build_design_doc_string():
        pass

class ImportDef(Decla):
    pass
class ClassDef(Decla): 
    pass
class MethodDef(Decla):
    def build(self):
        super().build()
        self.build_action()
    def build_action(self):
        dd = self.design_doc_string
        self.action = None
        for ak in action_keys:
            if dd.startswith(ak):
                self.action = ak 
                self.design_doc = self.design_doc_string[len(ak):].strip()
class AssignDef(Decla):
    pass 


def remove_c_style_comments(comment_str):
    comment_str = re.sub('/\\*+', '', comment_str)
    comment_str = re.sub('\\*+/', '', comment_str)
    comment_str = re.sub('^\\s*\\*\\s?', '', comment_str, flags=re.MULTILINE)
    comment_str = re.sub('\\n\\s*\\n', '\n', comment_str)
    return comment_str.strip()


def decla_list_2_string(dlist, str_spliter=' '):
    str_def = ''
    if dlist == None:
        return str_def
    for m in dlist:
        str_def += f'{str(m.toString())}{str_spliter}'
    if len(str_def) != 0:
        str_def = str_def[:-1]
    return str_def

def startswith_action_key(str_doc):
    for ak in action_keys:
        if str_doc.startswith(ak):
            return True 
    return False


