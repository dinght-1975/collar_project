package ai.d2c;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.*;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.FieldDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.TypeDeclaration;
import com.github.javaparser.ast.stmt.BlockStmt;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.type.Type;

public class JParserHelper {

    public static CompilationUnit parseCodeBlock(String str_code) {
        CompilationUnit cu = null;
        try {
            cu = StaticJavaParser.parse(str_code);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return cu;
    }

    public static void save(CompilationUnit cu, String fileName) throws IOException {
        // 将修改后的 CompilationUnit 写回文件
        try (FileWriter out = new FileWriter(fileName)) {
            out.write(cu.toString());
            return;
        }
    }

    public static MethodDeclaration setMethod(MethodDeclaration targetMethod, String strCode) {
        MethodDeclaration method = StaticJavaParser.parseMethodDeclaration(strCode);
        // 获取解析后方法的代码块并设置到目标方法中
        BlockStmt newBody = method.getBody().orElseThrow(() -> new IllegalArgumentException("新方法的代码块不能为空"));
        targetMethod.setBody(newBody);
        // 如果解析出的新方法有JavaDoc，替换目标方法的JavaDoc
        method.getJavadocComment().ifPresent(javadoc -> {
            targetMethod.setJavadocComment(javadoc);
        });
        return targetMethod;
    }

    /**
     * [功能说明]: 更新指定方法的JavaDoc注释。
     * [设计思想]: 该方法的设计思想是直接替换目标方法的JavaDoc注释，而不涉及方法的其他部分。
     * [实现步骤]:
     * 1. 调用 `method.setJavadocComment(newDoc)` 方法，将新的JavaDoc注释设置到目标方法中。
     * 2. 返回 `true` 表示更新成功。
     * :param method: 需要更新JavaDoc注释的目标方法。
     * :param newDoc: 新的JavaDoc注释内容。
     * :return: 返回 `true` 表示更新成功，始终返回 `true` 因为该方法没有失败的情况。
     */
    public static boolean updateMethodDoc(MethodDeclaration method, String newDoc) {
        method.setJavadocComment(newDoc);
        return true;
    }

    /*
     * new doc
     */
    public static boolean updateMethod(CompilationUnit cu, String newCode) {
        // Split the imports and method code
        String[] codeParts = newCode.split("(import\\s+[\\w\\.]+\\s*;\\s*)");
        String imports;
        String methods;
        // 如果newCode中没有import语句
        if (codeParts.length == 1) {
            // 没有import语句的情况，整个newCode就是方法
            // 没有import语句
            imports = "";
            // 全部内容都是方法
            methods = codeParts[0];
        } else {
            // 存在import语句的情况
            // import语句部分
            imports = codeParts[0];
            // 方法部分
            methods = codeParts[1];
        }
        // 判断是否包含类定义
        boolean hasClassDefinition = methods.contains("class ");
        CompilationUnit methodsCu;
        try {
            // 如果包含类定义，直接解析newCode
            if (hasClassDefinition) {
                methodsCu = StaticJavaParser.parse(methods);
            } else {
                // 如果没有class定义，则包裹成一个DummyClass
                String wrappedCode = "public class DummyClass { " + newCode + " }";
                methodsCu = StaticJavaParser.parse(wrappedCode);
            }
        } catch (Exception e) {
            System.err.println("Parsing error: " + e.getMessage());
            return false;
        }
        // Add imports and methods as described before
        // 解析imports部分
        if (!imports.isEmpty()) {
            CompilationUnit importsCu = StaticJavaParser.parse(imports);
            // 处理importsCu中的import
            List<ImportDeclaration> newImports = importsCu.getImports();
            for (ImportDeclaration newImport : newImports) {
                if (!cu.getImports().contains(newImport)) {
                    cu.addImport(newImport);
                }
            }
        }
        // Find the class in the current CompilationUnit (assuming there's only one)
        Optional<ClassOrInterfaceDeclaration> targetClass = cu.findFirst(ClassOrInterfaceDeclaration.class);
        if (targetClass.isPresent()) {
            ClassOrInterfaceDeclaration classDecl = targetClass.get();
            // Parse new methods and add/update them
            List<MethodDeclaration> newMethods = methodsCu.findAll(MethodDeclaration.class);
            for (MethodDeclaration newMethod : newMethods) {
                Optional<MethodDeclaration> existingMethod = findMethodBySignature(classDecl, newMethod);
                if (existingMethod.isPresent()) {
                    // Update the existing method
                    MethodDeclaration oldMethod = existingMethod.get();
                    // Replace method body
                    oldMethod.setBody(newMethod.getBody().orElse(null));
                    // Replace annotations
                    NodeList<AnnotationExpr> annotations = newMethod.getAnnotations();
                    oldMethod.setAnnotations(annotations);
                    // Replace Javadoc if present
                    if (newMethod.hasJavaDocComment()) {
                        oldMethod.setJavadocComment(newMethod.getJavadocComment().get());
                    }
                    // Replace method signature if necessary (return type, modifiers)
                    oldMethod.setType(newMethod.getType());
                    oldMethod.setModifiers(newMethod.getModifiers());
                } else {
                    // Add the new method if it doesn't exist
                    classDecl.addMember(newMethod);
                }
            }
        }
        return true;
    }

    // Helper method to find method by name and parameters (considering overloading)
    public static Optional<MethodDeclaration> findMethodBySignature(ClassOrInterfaceDeclaration classDecl, MethodDeclaration newMethod) {
        return classDecl.getMethodsByName(newMethod.getNameAsString()).stream().filter(existingMethod -> parametersMatch(existingMethod.getParameters(), newMethod.getParameters())).findFirst();
    }

    // Helper method to check if parameters match in overloaded methods
    private static boolean parametersMatch(NodeList<com.github.javaparser.ast.body.Parameter> existingParams, NodeList<com.github.javaparser.ast.body.Parameter> newParams) {
        if (existingParams.size() != newParams.size()) {
            return false;
        }
        for (int i = 0; i < existingParams.size(); i++) {
            Type existingType = existingParams.get(i).getType();
            Type newType = newParams.get(i).getType();
            if (!existingType.equals(newType)) {
                return false;
            }
        }
        return true;
    }

    public static MethodDeclaration parseMethodDecla(String str_code) {
        MethodDeclaration bs = null;
        try {
            bs = StaticJavaParser.parseMethodDeclaration(str_code);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return bs;
    }

    public static Map<String, Object> parseJavaFile(String file_name) {
        Map<String, Object> parsedData = new HashMap<>();
        try {
            // 解析Java文件
            File sourceFile = new File(file_name);
            CompilationUnit cu = StaticJavaParser.parse(sourceFile);
            // 获取 package
            Optional<PackageDeclaration> packageDeclaration = cu.getPackageDeclaration();
            packageDeclaration.ifPresent(pkg -> parsedData.put("package", pkg.getNameAsString()));
            // 获取 imports
            List<ImportDeclaration> imports = cu.getImports();
            parsedData.put("imports", imports.stream().map(ImportDeclaration::getNameAsString).toArray());
            // 获取类或接口
            List<TypeDeclaration<?>> types = cu.getTypes();
            for (TypeDeclaration<?> type : types) {
                if (type instanceof ClassOrInterfaceDeclaration) {
                    ClassOrInterfaceDeclaration classOrInterface = (ClassOrInterfaceDeclaration) type;
                    Map<String, Object> classInfo = new HashMap<>();
                    classInfo.put("name", classOrInterface.getNameAsString());
                    classInfo.put("isInterface", classOrInterface.isInterface());
                    // 提取类上的注释
                    classOrInterface.getComment().ifPresent(comment -> {
                        classInfo.put("classComment", comment.getContent());
                    });
                    // 获取 fields
                    List<FieldDeclaration> fields = classOrInterface.getFields();
                    Map<String, Object> fieldsMap = new HashMap<>();
                    for (FieldDeclaration field : fields) {
                        Map<String, Object> fieldInfo = new HashMap<>();
                        fieldInfo.put("field", field.toString());
                        // 提取字段的注释
                        field.getComment().ifPresent(comment -> {
                            fieldInfo.put("comment", comment.getContent());
                        });
                        fieldsMap.put(field.getVariables().get(0).getNameAsString(), fieldInfo);
                    }
                    classInfo.put("fields", fieldsMap);
                    // 获取 methods
                    List<MethodDeclaration> methods = classOrInterface.getMethods();
                    Map<String, Object> methodsMap = new HashMap<>();
                    for (MethodDeclaration method : methods) {
                        Map<String, Object> methodInfo = new HashMap<>();
                        methodInfo.put("name", method.getNameAsString());
                        // 获取方法全部内容
                        methodInfo.put("whole", method.toString());
                        methodsMap.put(method.getNameAsString(), methodInfo);
                    }
                    classInfo.put("methods", methodsMap);
                    parsedData.put("classOrInterface", classInfo);
                }
            }
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        }
        return parsedData;
    }

    public static CompilationUnit geCompilationUnit(String file_name) {
        CompilationUnit cu = null;
        try {
            StaticJavaParser.getParserConfiguration().setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_18);
            System.out.println(file_name);
            File sourceFile = new File(file_name);
            cu = StaticJavaParser.parse(sourceFile);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return cu;
    }
}
