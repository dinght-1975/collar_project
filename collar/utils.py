import xml.etree.ElementTree as ET


def indent(elem, level=0, str_spaces="    "):
    i = "\n" + (level) * str_spaces  # 4 spaces per level of indentation
    if len(elem):  # If the element has children
        if not elem.text or not elem.text.strip():
            elem.text = i + str_spaces
        else:
            elem.text = elem.text.replace("\n", "\n" + str_spaces)
        for child in elem:
            indent(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = elem.tail.replace("\n", "\n" + str_spaces)
        else:
            elem.tail = elem.tail.replace("\n", "\n" + str_spaces)
    else:
        if not elem.text or not elem.text.strip():
            elem.text = elem.text
        else:
            elem.text = elem.text.replace("\n", "\n" + str_spaces)
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
        else:
            elem.tail = elem.tail.replace("\n", "\n" + str_spaces)


def update_xml_by_element(file_path, new_element_str, namespace):
    # 解析新的 XML 字符串
    new_element = ET.fromstring(new_element_str)

    # 从新的 XML 元素中提取 id
    element_id = new_element.get("id")

    if element_id is None:
        print("The new XML element does not have an 'id' attribute.")
        return

    # 解析原始 XML 文件
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 查找具有指定 namespace 的 mapper 节点
    mapper_node = None
    for elem in root.iter("mapper"):
        if elem.get("namespace") == namespace:
            mapper_node = elem
            break

    if mapper_node is None:
        print(f"No mapper node found with namespace '{namespace}'.")
        return

    # 查找具有指定 id 的目标元素
    target_element = None
    for elem in mapper_node:
        if elem.get("id") == element_id:
            target_element = elem
            break

    if target_element is not None:
        # 更新目标元素的所有属性
        #for attr_name, attr_value in new_element.attrib.items():
        #    target_element.set(attr_name, attr_value)
        # 替换找到的元素内容，包括文本和子元素
        target_element_tail = target_element.tail
        str_spaces = target_element.tail.replace("\n", "")
        new_element.tail = target_element_tail
        indent(new_element)
        target_element.clear()
        for attr_name, attr_value in new_element.attrib.items():
            target_element.set(attr_name, attr_value)
        target_element.text = new_element.text  # 保留标签之间的文本
        for sub_elem in new_element:
            target_element.append(sub_elem)
            sub_elem.tail = sub_elem.tail  # 在每个子元素后添加换行符
        target_element.tail = target_element_tail
        print(f"Element with id '{element_id}' updated successfully in mapper '{namespace}'.")
    else:
        # 如果没有找到目标元素，则将新元素添加到 mapper 节点下
        mapper_node.append(new_element)
        new_element.tail = "\n"
        print(f"Element with id '{element_id}' not found, so it was added to mapper '{namespace}'.")

    # 将修改后的 XML 树写回文件
    tree.write(file_path, encoding='utf-8', xml_declaration=True)
    return True

def read_file_content(file_path):
    """
    读取文件内容
    :param file_path: 文件路径
    :return: 文件内容
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def write_file_content(file_path, content):
    """
    写入文件内容
    :param file_path: 文件路径
    :param content: 文件内容
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)