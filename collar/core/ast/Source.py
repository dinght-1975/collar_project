from abc import ABC, abstractmethod
import os,re
action_keys = [
    "-DES",
    "-CRE",
    "-MOD",
    "-DOC",
    "-QA",
    "-TEST",
    "-RUN"
]

class Source(ABC):
    def __init__(self, file_path):
        self.file_path = file_path
        file_name = os.path.basename(self.file_path)
        self.short_file_name = os.path.splitext(file_name)[0]
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
         self.def_string = f"{self.doc_string}\n{str(self.decla.toString())}"
    
    def build_signature(self):
        self.signature = str(self.decla.toString())
    
    def build_doc_string(self):
        decla = self.decla
        if hasattr(decla,"hasJavaDocComment") and decla.hasJavaDocComment():
            str_doc = str(decla.getJavadocComment().get().toString())
            self.doc_string = remove_c_style_comments(str_doc)
        else:
            str_body = str(decla.toString())
            str_doc = "";
            indx = str_body.find("/*-")
            if indx == -1:
                indx = str_body.find("/**")
            if (indx != -1):
                strTmp = str_body[indx:]
            else:
                self.doc_string = ""
                return
            indx = strTmp.find("*/")
            if (indx != -1):
               str_doc = strTmp[:indx + 2];
            self.doc_string = remove_c_style_comments(str_doc)

    def build(self):
        self.build_name()
        self.build_doc_string()
        self.build_signature()
        self.build_def_string()
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
        dd = self.doc_string
        self.action = None
        for ak in action_keys:
            if dd.startswith(ak):
                self.action = ak 
                self.design_doc = self.doc_string[len(ak):].strip()
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


