package ai.d2c;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class Util {

    public static boolean updateXMLByElement(String filePath, String newElementStr, String namespace) {
        try {
            // 解析新的 XML 字符串
            DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
            DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
            Document newElementDoc = dBuilder.parse(new ByteArrayInputStream(newElementStr.getBytes()));
            Element newElement = newElementDoc.getDocumentElement();
    
            // 从新的 XML 元素中提取 id
            String elementId = newElement.getAttribute("id");
            if (elementId == null || elementId.isEmpty()) {
                System.out.println("The new XML element does not have an 'id' attribute.");
                return false;
            }
    
            // 解析原始 XML 文件
            Document originalDoc = dBuilder.parse(new File(filePath));
            Element root = originalDoc.getDocumentElement();
    
            // 查找具有指定 namespace 的 mapper 节点
            NodeList mapperNodes = originalDoc.getElementsByTagName("mapper");
            Element mapperNode = null;
            for (int i = 0; i < mapperNodes.getLength(); i++) {
                Element elem = (Element) mapperNodes.item(i);
                if (namespace.equals(elem.getAttribute("namespace"))) {
                    mapperNode = elem;
                    break;
                }
            }
    
            if (mapperNode == null) {
                System.out.println("No mapper node found with namespace '" + namespace + "'.");
                return false;
            }
    
            // 查找具有指定 id 的目标元素
            NodeList targetElements = mapperNode.getElementsByTagName("*");
            Element targetElement = null;
            for (int i = 0; i < targetElements.getLength(); i++) {
                Element elem = (Element) targetElements.item(i);
                if (elementId.equals(elem.getAttribute("id"))) {
                    targetElement = elem;
                    break;
                }
            }
    
            if (targetElement != null) {
                // 替换找到的元素内容，包括文本和子元素
                targetElement.getParentNode().replaceChild(originalDoc.importNode(newElement, true), targetElement);
                System.out.println(
                        "Element with id '" + elementId + "' updated successfully in mapper '" + namespace + "'.");
            } else {
                // 如果没有找到目标元素，则将新元素添加到 mapper 节点下
                mapperNode.appendChild(originalDoc.importNode(newElement, true));
                System.out.println("Element with id '" + elementId + "' not found, so it was added to mapper '"
                        + namespace + "'.");
            }
    
            // 将修改后的 XML 树写回文件
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty(OutputKeys.INDENT, "no");
            transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "4");
            DOMSource source = new DOMSource(originalDoc);
            StreamResult result = new StreamResult(new File(filePath.replace(".xml", ".gen")));
            transformer.transform(source, result);
    
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
        return true;
    }

    // 移除C风格注释（类似 /* ... */）
    public static String removeCStyleComments(String commentStr) {
        if (commentStr.isEmpty()){
            return commentStr;
        }
        // 移除 /* 和 */
        commentStr = commentStr.replaceAll("/\\*+", "").replaceAll("\\*+/", "");
    
        // 移除每行开头的 *
        Pattern pattern = Pattern.compile("^\\s*(?:<[^>]+>\\s*)*\\*\\s?", Pattern.MULTILINE);
        Matcher matcher = pattern.matcher(commentStr);
        StringBuffer cleanedComment = new StringBuffer();
    
        while (matcher.find()) {
            matcher.appendReplacement(cleanedComment, "");
        }
        matcher.appendTail(cleanedComment);
    
        return cleanedComment.toString().trim(); // 去掉首尾空格
    }

    public static String removeComments(String methodDefinition) {
        // 去除 JavaDoc 注释和多行注释（/*...*/）
        String methodWithoutMultilineComments = removeMultilineComments(methodDefinition);
        
        // 去除单行注释 (//...)
        String methodWithoutSinglelineComments = removeSinglelineComments(methodWithoutMultilineComments);
        
        // 移除多余的空行
        String methodCleaned = removeExtraEmptyLines(methodWithoutSinglelineComments);
        
        return methodCleaned.trim();
    }

    private static String removeMultilineComments(String input) {
        // 正则表达式去除多行注释
        Pattern pattern = Pattern.compile("/\\*.*?\\*/", Pattern.DOTALL);
        Matcher matcher = pattern.matcher(input);
        return matcher.replaceAll("");
    }

    private static String removeSinglelineComments(String input) {
        // 正则表达式去除单行注释
        Pattern pattern = Pattern.compile("//.*");
        Matcher matcher = pattern.matcher(input);
        return matcher.replaceAll("");
    }

    private static String removeExtraEmptyLines(String input) {
        // 正则表达式去除多余的空行
        return input.replaceAll("\\n\\s*\\n", "\n");
    }
    
}
