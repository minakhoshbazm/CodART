import antlr4
from antlr4.Token import CommonToken
import antlr4.tree

from antlr4_java9.Java9Parser import Java9Parser, CommonTokenStream
from antlr4_java9.Java9Listener import Java9Listener
from javaparsergen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from javaparsergen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

class Program:
    def __init__(self):
        self.packages = {}
    def __str__(self):
        return str(self.packages)

class Package:
    def __init__(self):
        self.name = None
        self.classes = {}
    def __str__(self):
        return str(self.name) + " " + str(self.classes)

class TokensInfo:
    """Note that start and stop are inclusive."""

    def __init__(self, parser_context = None):
        if parser_context is not None:
            self.token_stream: CommonTokenStream = parser_context.parser.getTokenStream()
            self.start: int = parser_context.start.tokenIndex
            self.stop: int = parser_context.stop.tokenIndex
        else:
            self.token_stream: CommonTokenStream = None
            self.start: int = None
            self.stop: int = None
    def get_token_index(self, tokens : list,start : int , stop : int):

        return tokens[start:stop]

class FileInfo:
    def __init__(self, filename: str = None, package_name: str = None):
        self.filename: str = None
        self.package_name: str = None
        self.all_imports = []
        self.package_imports = []
        self.class_imports = []
    def has_imported_class(self, package_name: str, class_name: str) -> bool:
        if self.package_name == package_name:
            return True
        return (
            any(lambda x: x.package_name == package_name for package_import in self.package_imports)
            or any(lambda x: x.package_name == package_name and x.class_name == class_name for class_import in self.class_imports)
        )
    def has_imported_package(self, package_name: str):
        if self.package_name == package_name:
            return True
        return(
            any(lambda x: x.package_name == package_name for package_import in self.package_imports)
        )

class SingleFileElement:
    """The base class for those elements that are extracted from a single file"""

    def __init__(self, parser_context, filename: str = None, _file_info: FileInfo = None):
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = _file_info

    def get_token_stream(self) -> CommonTokenStream:
        return self.parser_context.parser.getTokenStream()

    def get_tokens_info(self) -> TokensInfo:
        return TokensInfo(
            self.parser_context
        )

    def get_first_symbol(self) -> CommonToken:
        first_terminal = self.parser_context
        while not isinstance(first_terminal, antlr4.tree.Tree.TerminalNode):
            first_terminal = first_terminal.getChild(0)

        return first_terminal.getSymbol()

    def get_last_symbol(self) -> CommonToken:
        last_terminal = self.parser_context
        while not isinstance(last_terminal, antlr4.tree.Tree.TerminalNode):
            last_terminal = last_terminal.getChild(last_terminal.getChildCount() - 1)

        return last_terminal.getSymbol()

    def get_file_position_range(self) -> tuple:
        return (
            self.get_first_symbol().start,
            self.get_last_symbol().stop
        )

    def get_text_from_file(self, filename = None) -> str:
        if filename is None:
            filename = self.filename
        if filename is None:
            return None
        file = open(filename, 'r')
        text = file.read()
        file.close()

        return text[self.get_first_symbol().start:self.get_last_symbol().stop+1]

class ClassImport(SingleFileElement):
    """import package_name.class_name;"""
    def __init__(self,
                 package_name: str = None,
                 class_name: str = None,
                 parser_context: Java9Parser.SingleTypeImportDeclarationContext = None,
                 filename: str = None,
                 file_info: FileInfo = None):
        self.package_name = package_name
        self.class_name = class_name
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = file_info
    def __str__(self):
        return "import " + str(self.package_name) + '.' + str(self.class_name)

class PackageImport(SingleFileElement):
    """import package_name.*;"""
    def __init__(self,
                 package_name: str = None,
                 parser_context: Java9Parser.SingleTypeImportDeclarationContext = None,
                 filename: str = None,
                 file_info: FileInfo = None):
        self.package_name = package_name
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = file_info
    def __str__(self):
        return "import " + str(self.package_name) + ".*"

class Class(SingleFileElement):
    def __init__(self,
                 name: str = None,
                 super_class_name: str = None,
                 package_name: str = None,
                 parser_context: Java9Parser.NormalClassDeclarationContext = None,
                 filename: str = None,
                 file_info: FileInfo = None):
        self.modifiers = []
        self.name = name
        self.superclass_name = None
        self.superinterface_names = []
        self.fields = {}
        self.methods = {}
        self.package_name = package_name
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = file_info
        self.body_context = None;
    def __str__(self):
        return str(self.modifiers) +  " " + str(self.name) \
            + ((" extends " + str(self.superclass_name)) if self.superclass_name is not None else "") \
            + ((" implements " + str(self.superinterface_names)) if len(self.superinterface_names) > 0 else "") \
            + " " + str(self.fields) \
            + " " + str(self.methods)

# TODO Add Interface

class Field(SingleFileElement):
    def __init__(self,
                 datatype: str = None,
                 name: str = None,
                 initializer: str = None,
                 package_name: str = None,
                 class_name: str = None,
                 parser_context: Java9Parser.FieldDeclarationContext = None,
                 filename: str = None,
                 file_info: FileInfo = None):
        self.modifiers = []
        self.datatype = datatype
        self.name = name
        self.initializer = initializer
        self.neighbor_names = []
        self.all_variable_declarator_contexts = []
        self.index_in_variable_declarators: int = None
        self.package_name = package_name
        self.class_name = class_name
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = file_info
    def __str__(self):
        return str(self.modifiers) +  " " + str(self.datatype) + " " + str(self.name)

class Method(SingleFileElement):
    def __init__(self,
                 returntype: str = None,
                 name: str = None,
                 body_text: str = None,
                 package_name: str = None,
                 class_name: str = None,
                 parser_context: Java9Parser.MethodDeclarationContext = None,
                 filename: str = None,
                 file_info: FileInfo = None):
        self.modifiers = []
        self.returntype = returntype
        self.name = name
        self.parameters = []
        self.body_text = body_text
        self.body_method_invocations = {}
        self.body_local_vars_and_expr_names = [] # Type: either LocalVariable, ExpressionName or MethodInvocation
        self.package_name = package_name
        self.class_name = class_name
        self.parser_context = parser_context
        self.filename = filename
        self.file_info = file_info
        self.formalparam_context = None
        self.body_method_invocations_without_typename = {}
        self.method_declaration_context = None

    def __str__(self):
        return str(self.modifiers) +  " " + str(self.returntype) + " " + str(self.name) \
            + str(tuple(self.parameters))

class LocalVariable:
    def __init__(self, datatype: str = None, identifier: str = None, parser_context: Java9Parser.LocalVariableDeclarationContext = None):
        self.datatype = datatype
        self.identifier = identifier
        self.parser_context = parser_context

class ExpressionName:
    def __init__(self, dot_separated_identifiers: list):
        self.dot_separated_identifiers = dot_separated_identifiers

class MethodInvocation:
    def __init__(self, dot_separated_identifiers: list, parser_context: Java9Parser.MethodInvocationContext = None):
        self.dot_separated_identifiers = dot_separated_identifiers
        self.parser_context = parser_context

class UtilsListener(Java9Listener):

    def __init__(self, filename):
        self.package = Package()

        self.current_class_identifier = None
        self.current_class_identifier_temp = None
        self.nest_count = 0

        self.current_method_identifier = None
        self.current_method = None

        self.current_local_var_type = None
        self.current_local_var_ctx = None

        self.current_field_decl = None
        self.current_field_ids = None
        self.current_field_dims = None
        self.current_field_inits = None
        self.current_field_var_ctxs = None

        self.filename = filename
        self.file_info = FileInfo(filename=filename)

    def enterPackageDeclaration(self, ctx:Java9Parser.PackageDeclarationContext):
        self.package.name = ctx.packageName().getText()
        self.file_info.package_name = self.package.name

    def enterSingleTypeImportDeclaration(self, ctx:Java9Parser.SingleTypeImportDeclarationContext):
        typename: Java9Parser.TypeNameContext = ctx.typeName()
        p = None
        if typename.packageOrTypeName() is not None:
            p = typename.packageOrTypeName().getText()
        c = typename.identifier().getText()
        class_import = ClassImport(
            package_name=p,
            class_name=c,
            parser_context=ctx,
            filename=self.filename,
            file_info=self.file_info
        )
        self.file_info.all_imports.append(class_import)
        self.file_info.class_imports.append(class_import)

    def enterTypeImportOnDemandDeclaration(self, ctx:Java9Parser.TypeImportOnDemandDeclarationContext):
        p = ctx.packageOrTypeName().getText()
        package_import = PackageImport(
            package_name=p,
            parser_context=ctx,
            filename=self.filename,
            file_info=self.file_info
        )
        self.file_info.all_imports.append(package_import)
        self.file_info.package_imports.append(package_import)

    def enterSingleStaticImportDeclaration(self, ctx:Java9Parser.SingleStaticImportDeclarationContext):
        pass

    def enterStaticImportOnDemandDeclaration(self, ctx:Java9Parser.StaticImportOnDemandDeclarationContext):
        pass

    def enterNormalClassDeclaration(self, ctx:Java9Parser.NormalClassDeclarationContext):
        if self.current_class_identifier is None and self.nest_count == 0:
            self.current_class_identifier = ctx.identifier().getText()
            self.current_class_ctx = ctx.identifier()
            current_class = Class(
                package_name=self.package.name,
                parser_context=ctx,
                filename=self.filename,
                file_info=self.file_info
            )
            for modifier in ctx.getChildren(lambda x: type(x) == Java9Parser.ClassModifierContext):
                current_class.modifiers.append(modifier.getText())
            current_class.name = self.current_class_identifier
            self.package.classes[current_class.name] = current_class

        else:
            if self.nest_count == 0:
                self.current_class_identifier_temp = self.current_class_identifier
                self.current_class_identifier = None
            self.nest_count += 1

    def enterSuperclass(self, ctx:Java9Parser.SuperclassContext):
        if self.current_class_identifier is not None:
            self.package.classes[self.current_class_identifier].superclass_name = ctx.classType().getText()

    def enterSuperinterfaces(self, ctx:Java9Parser.SuperinterfacesContext):
        if self.current_class_identifier is not None:
            _class = self.package.classes[self.current_class_identifier]
            for interface_type in ctx.interfaceTypeList().getChildren(lambda x: type(x) == Java9Parser.InterfaceTypeContext):
                _class.superinterface_names.append(interface_type.getText())

    def enterClassBody(self, ctx:Java9Parser.ClassBodyContext):
        if self.current_class_identifier is not None:
            self.package.classes[self.current_class_identifier].body_context = ctx;

    def exitNormalClassDeclaration(self, ctx:Java9Parser.NormalClassDeclarationContext):
        if self.nest_count > 0:
            self.nest_count -= 1
            if self.nest_count == 0:
                self.current_class_identifier = self.current_class_identifier_temp
                self.current_class_identifier_temp = None
        elif self.current_class_identifier is not None:
                self.current_class_identifier = None

    def enterFormalParameterList(self, ctx: Java9Parser.FormalParameterListContext):
        if self.current_method is not None:
            self.current_method.formalparam_context = ctx
    def enterMethodDeclaration(self, ctx:Java9Parser.MethodDeclarationContext):
        if self.current_class_identifier is not None:
            method_header = ctx.methodHeader()
            self.current_method_identifier = method_header.methodDeclarator().identifier().getText()

            method = Method(
                package_name=self.package.name,
                class_name=self.current_class_identifier,
                parser_context=ctx,
                filename=self.filename,
                file_info=self.file_info
            )
            for modifier in ctx.getChildren(lambda x: type(x) == Java9Parser.MethodModifierContext):
                method.modifiers.append(modifier.getText())
            method.returntype = method_header.result().getText()
            method.name = self.current_method_identifier

            self.package.classes[self.current_class_identifier].methods[method.name] = method
            self.current_method = method

    def enterMethodHeader(self, ctx:Java9Parser.MethodHeaderContext):
        if self.current_method is not None:
            self.current_method.method_declaration_context = ctx
    def enterFormalParameter(self, ctx:Java9Parser.FormalParameterContext):
        if self.current_method is not None:
            self.current_method.parameters.append(
                (ctx.unannType().getText(), ctx.variableDeclaratorId().identifier().getText())
            )

    def enterMethodBody(self, ctx:Java9Parser.MethodBodyContext):
        if self.current_method is not None:
            self.current_method.body_text = ctx.getText()
            pass

    def exitMethodDeclaration(self, ctx:Java9Parser.MethodDeclarationContext):
        self.current_method_identifier = None
        self.current_method = None

    def enterMethodInvocation(self, ctx:Java9Parser.MethodInvocationContext):
        if self.current_method is not None :
            #for typename in ctx.getChildren(lambda x: type(x) == Java9Parser.TypeNameContext):
            #    self.current_method.body_method_invocations.append(typename)
            if ctx.typeName() != None:
                if ctx.typeName().identifier() not in self.current_method.body_method_invocations:
                    self.current_method.body_method_invocations[ctx.typeName().identifier()] = [ctx.identifier().getText()]
                else:
                    self.current_method.body_method_invocations[ctx.typeName().identifier()].append(
                        ctx.identifier().getText())
            else:
                if ctx.methodName() != None:
                    if self.current_class_ctx not in self.current_method.body_method_invocations_without_typename:
                        self.current_method.body_method_invocations_without_typename[self.current_class_ctx] = [ctx.methodName().identifier()]
                    else:
                        self.current_method.body_method_invocations_without_typename[self.current_class_ctx].append(
                            ctx.methodName().identifier())
            #MethodInvocation
            txt = ctx.getText()
            ids = txt[:txt.find('(')].split('.')
            self.current_method.body_local_vars_and_expr_names.append(
                MethodInvocation(ids, ctx)
            )


    def enterLocalVariableDeclaration(self, ctx:Java9Parser.LocalVariableDeclarationContext):
        if self.current_method is not None:
            self.current_local_var_type = ctx.unannType().getText()
            self.current_local_var_ctx = ctx
            # The rest in: enterVariableDeclarator

    def exitLocalVariableDeclaration(self, ctx:Java9Parser.LocalVariableDeclarationContext):
        self.current_local_var_type = None

    def enterExpressionName(self, ctx:Java9Parser.ExpressionNameContext):
        if self.current_method is not None:
            names = [ctx.identifier().getText()]
            c = ctx.ambiguousName()
            while c is not None:
                names.insert(0, c.identifier().getText())
                c = c.ambiguousName()
            self.current_method.body_local_vars_and_expr_names.append(ExpressionName(names))

    def enterFieldDeclaration(self, ctx:Java9Parser.FieldDeclarationContext):
        if self.current_class_identifier is not None:
            modifiers = []
            for modifier in ctx.getChildren(lambda x: type(x) == Java9Parser.FieldModifierContext):
                modifiers.append(modifier.getText())
            datatype = ctx.unannType().getText()
            self.current_field_decl = (modifiers, datatype, ctx)
            self.current_field_ids = []
            self.current_field_dims = []
            self.current_field_inits = []
            self.current_field_var_ctxs = []

    def enterVariableDeclarator(self, ctx:Java9Parser.VariableDeclaratorContext):
        if self.current_field_decl is not None:
            self.current_field_ids.append(ctx.variableDeclaratorId().identifier().getText())
            dims = ""
            dims_ctx = ctx.variableDeclaratorId().dims()
            if dims_ctx is not None:
                dims = dims_ctx.getText()
            self.current_field_dims.append(dims)
            init = None
            init_ctx = ctx.variableInitializer()
            if init_ctx is not None:
                init = init_ctx.getText()
            self.current_field_inits.append(init)
            self.current_field_var_ctxs.append(ctx)
        if self.current_local_var_type is not None:
            if self.current_method is not None:
                dims = ""
                if ctx.variableDeclaratorId().dims() is not None:
                    dims = ctx.variableDeclaratorId().dims().getText()
                self.current_method.body_local_vars_and_expr_names.append(
                    LocalVariable(self.current_local_var_type + dims, ctx.variableDeclaratorId().identifier().getText(), self.current_local_var_ctx)
                )

    def exitFieldDeclaration(self, ctx:Java9Parser.FieldDeclarationContext):
        if self.current_class_identifier is not None:
            for i in range(len(self.current_field_ids)):
                field_id = self.current_field_ids[i]
                dims = self.current_field_dims[i]
                field_init = self.current_field_inits[i]
                var_ctx = self.current_field_var_ctxs[i]
                field = Field(
                    package_name=self.package.name,
                    class_name=self.current_class_identifier,
                    parser_context=self.current_field_decl[2],
                    filename=self.filename,
                    file_info=self.file_info
                )
                field.modifiers = self.current_field_decl[0]
                field.datatype = self.current_field_decl[1] + dims
                field.name = field_id
                field.initializer = field_init
                field.neighbor_names = [ x for x in self.current_field_ids if x != field_id ]
                field.all_variable_declarator_contexts = self.current_field_var_ctxs
                field.index_in_variable_declarators = i
                self.package.classes[self.current_class_identifier].fields[field.name] = field
            self.current_field_decl = None
