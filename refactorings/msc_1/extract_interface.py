import os

import utils_listener_fast
import utils

def extract_interface(source_filenames: list,
                      package_name: str,
                      class_names: list,
                      method_keys: list,
                      interface_name: str,
                      interface_filename: str,
                      filename_mapping = lambda x: (x[:-5] if x.endswith(".java") else x) + ".re.java") -> bool:

    program = utils.get_program(source_filenames, print_status=True)

    if package_name not in program.packages \
            or any(
                class_name not in program.packages[package_name].classes
                    for class_name in class_names
            ) \
            or any(
                method_key not in program.packages[package_name].classes[class_name].methods
                    for class_name in class_names for method_key in method_keys
            ):
        return False

    method_returntypes = {}
    method_parameters = {}
    method_names = []
    for method_key in method_keys:
        method_names.append(method_key[:method_key.find('(')])

    rewriter = utils.Rewriter(program, filename_mapping)

    for class_name in class_names:
        c: utils_listener_fast.Class = program.packages[package_name].classes[class_name]
        # Add implements to the class
        has_superinterface = False
        if c.parser_context.IMPLEMENTS() is not None: # old: c.parser_context.superinterfaces()
            t = utils_listener_fast.TokensInfo(c.parser_context.typeList()) # old: c.parser_context.superinterfaces()
            has_superinterface = True
        elif c.parser_context.EXTENDS() is not None: # old: c.parser_context.superclass()
            t = utils_listener_fast.TokensInfo(c.parser_context.typeType()) # old: c.parser_context.superclass()
        elif c.parser_context.typeParameters() is not None:
            t = utils_listener_fast.TokensInfo(c.parser_context.typeParameters())
        else:
            # old: TokensInfo(c.parser_context.identifier())
            t = utils_listener_fast.TokensInfo(c.parser_context)
            t.stop = c.parser_context.IDENTIFIER().getSymbol().tokenIndex
        rewriter.insert_after(t, (", " if has_superinterface else " implements ") + interface_name)
        for method_key in method_keys:
            m: utils_listener_fast.Method = c.methods[method_key]
            # Check if the return types / parameter types are the same
            # Or add to dictionary
            if method_key in method_returntypes:
                if method_returntypes[method_key] != m.returntype:
                    return False
                if len(method_parameters[method_key]) != len(m.parameters):
                    return False
                for i in range(len(m.parameters)):
                    if method_parameters[method_key][i][0] != m.parameters[i][0]:
                        return False
            else:
                method_returntypes[method_key] = m.returntype
                method_parameters[method_key] = m.parameters
            # Manage method modifiers
            if len(m.modifiers_parser_contexts) > 0:
                t = utils_listener_fast.TokensInfo(m.modifiers_parser_contexts[0])
            else:
                t = m.get_tokens_info()
            rewriter.insert_before_start(
                t, # old: m.get_tokens_info() # without requiring t
                ("" if "@Override" in m.modifiers else "@Override\n    ")
                + ("" if "public" in m.modifiers else "public ")
            )
            for i in range(len(m.modifiers)):
                mm = m.modifiers[i]
                if mm == "private" or mm == "protected":
                    t = utils_listener_fast.TokensInfo(m.modifiers_parser_contexts[i]) # old: m.parser_context.methodModifier(i)
                    rewriter.replace(t, "")

    # Change variable types to the interface if only interface methods are used.
    for package_name in program.packages:
        p: utils_listener_fast.Package = program.packages[package_name]
        for class_name in p.classes:
            c: utils_listener_fast.Class = p.classes[class_name]
            fields_of_interest = {}
            for fn in c.fields:
                f: utils_listener_fast.Field = c.fields[fn]
                d = False
                for cn in class_names:
                    if (f.datatype == cn and f.file_info.has_imported_class(package_name, cn)) \
                            or (package_name is not None and f.datatype == package_name + '.' + cn):
                        d = True
                        break
                if d and "private" in f.modifiers:
                    fields_of_interest[f.name] = f
            for method_key in c.methods:
                m: utils_listener_fast.Method = c.methods[method_key]
                vars_of_interest = {}
                for item in m.body_local_vars_and_expr_names:
                    if isinstance(item, utils_listener_fast.LocalVariable):
                        for cn in class_names:
                            if (item.datatype == cn and c.file_info.has_imported_class(package_name, cn)) \
                                    or (package_name is not None and item.datatype == package_name + '.' + cn):
                                vars_of_interest[item.identifier] = item
                                break
                    if isinstance(item, utils_listener_fast.MethodInvocation):
                        if len(item.dot_separated_identifiers) == 2 or \
                                (len(item.dot_separated_identifiers) == 3 and item.dot_separated_identifiers[0] == "this"):
                            if item.dot_separated_identifiers[-2] in vars_of_interest:
                                if item.dot_separated_identifiers[-1] not in method_names:
                                    vars_of_interest.pop(item.dot_separated_identifiers[-2])
                            elif item.dot_separated_identifiers[-2] in fields_of_interest \
                                    and item.dot_separated_identifiers[-1] not in method_names:
                                fields_of_interest.pop(item.dot_separated_identifiers[-2])
                for var_name in vars_of_interest:
                    var = vars_of_interest[var_name]
                    if m.file_info.has_imported_package(package_name):
                        # old: var.parser_context.unannType()
                        rewriter.replace(utils_listener_fast.TokensInfo(var.parser_context.typeType()), interface_name)
                    else:
                        if package_name is None:
                            break
                        # old: var.parser_context.unannType()
                        rewriter.replace(utils_listener_fast.TokensInfo(var.parser_context.typeType()), package_name + '.' + interface_name)
            for field_name in fields_of_interest:
                f = fields_of_interest[field_name]
                if c.file_info.has_imported_package(package_name):
                    typename = interface_name
                else:
                    if package_name is None:
                        break
                    typename = package_name + '.' + interface_name
                if len(f.neighbor_names) == 0:
                    rewriter.replace(utils_listener_fast.TokensInfo(f.parser_context.typeType()), typename) # old: f.parser_context.unannType()
                else:
                    if not any(nn in fields_of_interest for nn in f.neighbor_names):
                        t = utils_listener_fast.TokensInfo(f.all_variable_declarator_contexts[f.index_in_variable_declarators])
                        if f.index_in_variable_declarators == 0:
                            t.stop = utils_listener_fast.TokensInfo(f.all_variable_declarator_contexts[f.index_in_variable_declarators + 1]).start - 1
                        else:
                            t.start = utils_listener_fast.TokensInfo(f.all_variable_declarator_contexts[f.index_in_variable_declarators - 1]).start + 1
                        rewriter.replace(t, "")
                        rewriter.insert_after(
                            f.get_tokens_info(),
                            "\n    private " + typename + " " + f.name + (" = " + f.initializer + ";" if f.initializer is not None else ";")
                        )

    # Create the interface
    interface_file_content = (
        "package " + package_name +";\n\n"
        + "public interface " + interface_name + "\n"
        + "{\n"
    )
    for method_key in method_keys:
        method_name = method_key[:method_key.find('(')]
        interface_file_content += "    " + method_returntypes[method_key] + " " + method_name + "("
        if len(method_parameters[method_key]) > 0:
            interface_file_content += method_parameters[method_key][0][0] + " " + method_parameters[method_key][0][1]
        for i in range(1, len(method_parameters[method_key])):
            param = method_parameters[method_key][i]
            interface_file_content += ", " + param[0] + " " + param[1]
        interface_file_content += ");\n"
    interface_file_content += "}\n"

    if not os.path.exists(interface_filename[:interface_filename.rfind('/')]):
        os.makedirs(interface_filename[:interface_filename.rfind('/')])
    file = open(interface_filename, "w+")
    file.write(interface_file_content)
    file.close()

    rewriter.apply()
    return True

def test():
    print("Testing extract_interface...")
    filenames = [
        "tests/extract_interface/A.java",
        "tests/extract_interface/B.java",
        "tests/extract_interface/C.java",
        "tests/extract_interface/D.java",
        "tests/extract_interface/E.java",
        "tests/extract_interface/U.java",
    ]
    if extract_interface(filenames, "test", ["A", "B"], ["a(int,float)", "b()"], "Iab", "tests/extract_interface/Iab.re.java"):
        print("A, B: Success!")
    else:
        print("A, B: Cannot refactor.")
    for third_class in ["C", "D", "E"]:
        if extract_interface(filenames, "test", ["A", "B", third_class], ["a(int,float)", "b()"], "Iab", "tests/extract_interface/Iab.re.java"):
            print("A, B, " + third_class + ": Success!")
        else:
            print("A, B, " + third_class + ": Cannot refactor.")

def test_ant():
    """
    target_files = [
        "tests/apache-ant/main/org/apache/tools/ant/input/InputRequest.java",
        "tests/apache-ant/main/org/apache/tools/ant/input/MultipleChoiceInputRequest.java"
    ]
    """
    ant_dir = "tests/apache-ant-1-7-0"
    print("Success!" if extract_interface(
        utils.get_filenames_in_dir(ant_dir),
        "org.apache.tools.ant.input",
        ["InputRequest", "MultipleChoiceInputRequest"],
        [ "isInputValid()" ],
        "ExtractedInterface",
        "tests/extract_interface_ant/ExtractedInterface.java",
        lambda x: "tests/extract_interface_ant/" + x[len(ant_dir):]
    ) else "Cannot refactor.")

if __name__ == "__main__":
    test()
