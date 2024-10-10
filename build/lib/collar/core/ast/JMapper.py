from JSource import JSource
import os
import utils
class JMapper(JSource):
    pass
    def replace_method_code(self, method, new_code):
        if self.is_mapper():
            return self.update_mapper_xml(new_code)
        
    def update_mapper_xml(self, str_code):
        file_name = self.get_mapper_xml_file_name()
        return utils.update_xml_by_element(file_name, str_code, f"{self.full_module_name}") 
    
    def get_mapper_xml_file_name(self):
        str_package = self.module_name
        str_class_name = self.short_file_name
        arr_strs = str_package.split(".")
        last_node = arr_strs[-1]
        relative_paths=["resources","mapper",last_node]
        xml_file_name = os.path.join(self.main_path,*relative_paths, f"{str_class_name}.xml")
        return xml_file_name   
    
    def get_table_def(self):
        str_context = ""
        str_package = self.module_path
        arr_strs = str_package.split(".")
        last_node = arr_strs[-1]
        ddl_file_name = os.path.join(self.project_path, "sql", "DDL", f"{last_node}.init.sql")
        if not os.path.exists(ddl_file_name):
            print(f"File {ddl_file_name} doesn't exist.")
            return str_context
        content = utils.read_file_content(ddl_file_name)
        str_context = f"Mapper XML 的定义:\n{content}"
        return str_context
    
    def get_xml_def(self):
        str_context = ""
        xml_file_name = self.get_mapper_xml_file_name()
        if not os.path.exists(xml_file_name):
            print(f"File {xml_file_name} doesn't exist.")
            return str_context
        content = utils.read_file_content(xml_file_name)
        str_context = f"数据库表的定义:\n{content}"
        return str_context
    
    def get_extra_def(self):
        return self.get_table_def() + self.get_xml_def()