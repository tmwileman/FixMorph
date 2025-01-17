from app.common import definitions, values
from app.common.utilities import execute_command, error_exit, get_code, backup_file, \
    show_partial_diff, backup_file_orig, restore_file_orig, replace_file, get_code_range, \
    find_file_using_path
from app.tools import converter, emitter, finder, extractor, logger
from app.ast import ast_generator

import os
import sys

file_index = 1
backup_file_list = dict()
FILENAME_BACKUP = "temp-source"
TOOL_AST_PATCH = "patchweave"


def restore_files():
    global backup_file_list
    emitter.warning("Restoring files...")
    for b_file in backup_file_list.keys():
        backup_file = backup_file_list[b_file]
        backup_command = "cp backup/" + backup_file + " " + b_file
        execute_command(backup_command)
    emitter.warning("Files restored")


def execute_ast_transformation(script_path, source_file_info):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    file_a, file_b, file_c, file_d = source_file_info
    emitter.normal("\t[action] executing AST transformation")

    output_file = definitions.DIRECTORY_OUTPUT + str(file_index) + "_temp." + file_c[-1]
    backup_command = ""
    # We add file_c into our dict (changes) to be able to backup and copy it

    if file_c not in backup_file_list.keys():
        filename = file_c.split("/")[-1]
        backup_file = str(file_index) + "_" + filename
        backup_file_list[file_c] = backup_file
        backup_command += "cp " + file_c + " " + definitions.DIRECTORY_BACKUP + "/" + backup_file
    # print(backup_command)

    if backup_command:
        execute_command(backup_command)

    parameters = " -s=" + definitions.PATCH_SIZE

    if values.DONOR_REQUIRE_MACRO:
        parameters += " " + values.DONOR_PRE_PROCESS_MACRO + " "

    if values.TARGET_REQUIRE_MACRO:
        parameters += " " + values.TARGET_PRE_PROCESS_MACRO + " "

    parameters += " -script=" + script_path + " -source=" + file_a
    parameters += " -destination=" + file_b + " -target=" + file_c
    parameters += " -map=" + definitions.FILE_NAMESPACE_MAP_LOCAL

    patch_command = definitions.PATCH_COMMAND + parameters + " > " + definitions.FILE_TEMP_FIX \
                    + " 2> " + definitions.FILE_ERROR_LOG

    ret_code = int(execute_command(patch_command))

    if ret_code == 0:
        move_command = "cp " + definitions.FILE_TEMP_FIX + " " + file_d
        execute_command(move_command)
        show_partial_diff(file_c, file_d)

    else:
        error_exit("\t AST transformation FAILED")

    if os.stat(file_d).st_size == 0:
        error_exit("\t AST transformation FAILED")

    if values.BREAK_WEAVE:
        exit()

    return ret_code


def execute_diff_transformation(diff_file, source_file_info):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    file_a, file_b, file_c, file_d = source_file_info
    emitter.normal("\t[action] executing diff transformation")
    output_file = definitions.DIRECTORY_OUTPUT + str(file_index) + "_temp." + file_c[-1]
    backup_command = ""
    # We add file_c into our dict (changes) to be able to backup and copy it

    if file_c not in backup_file_list.keys():
        filename = file_c.split("/")[-1]
        backup_file = str(file_index) + "_" + filename
        backup_file_list[file_c] = backup_file
        backup_command += "cp " + file_c + " " + definitions.DIRECTORY_BACKUP + "/" + backup_file
    # print(backup_command)
    if backup_command:
        execute_command(backup_command)

    patch_command = definitions.LINUX_PATCH_COMMAND + " "
    if values.DEFAULT_OPERATION_MODE == 2:
        patch_command += " --context "
    patch_command += file_c + " " + diff_file + " -o " + definitions.FILE_TEMP_FIX
    ret_code = int(execute_command(patch_command))

    if ret_code == 0:
        move_command = "cp " + definitions.FILE_TEMP_FIX + " " + file_d
        execute_command(move_command)
        show_partial_diff(file_c, file_d)

    else:
        error_exit("\t diff transformation FAILED")

    if os.stat(file_d).st_size == 0:
        error_exit("\t diff transformation FAILED")

    if values.BREAK_WEAVE:
        exit()

    return ret_code


def show_patch(file_a, file_b, file_c, file_d, index):
    emitter.highlight("\tOriginal Patch")
    original_patch_file_name = definitions.DIRECTORY_OUTPUT + "/" + index + "-original-patch"
    generated_patch_file_name = definitions.DIRECTORY_OUTPUT + "/" + index + "-generated-patch"
    diff_command = "diff -ENZBbwr "
    if values.DEFAULT_OUTPUT_FORMAT == "unified":
        diff_command += " -u "
    diff_command += file_a + " " + file_b + " > " + original_patch_file_name
    execute_command(diff_command)
    with open(original_patch_file_name, 'r', encoding='utf8', errors="ignore") as diff:
        diff_line = diff.readline().strip()
        while diff_line:
            emitter.special("\t\t" + diff_line)
            diff_line = diff.readline().strip()

    emitter.highlight("\tGenerated Patch")
    diff_command = "diff -ENZBbwr "
    if values.DEFAULT_OUTPUT_FORMAT == "unified":
        diff_command += " -u "
    diff_command += file_c + " " + file_d + " > " + generated_patch_file_name
    # print(diff_command)
    execute_command(diff_command)
    if os.path.getsize(generated_patch_file_name) == 0:
        error_exit("diff transformation FAILED\n\tfailed to generate a backporting")
    with open(generated_patch_file_name, 'r', encoding='utf8', errors="ignore") as diff:
        diff_line = diff.readline().strip()
        while diff_line:
            emitter.special("\t\t" + diff_line)
            diff_line = diff.readline().strip()


def insert_code(patch_code, source_path, line_number):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    content = ""
    if os.path.exists(source_path):
        with open(source_path, 'r', encoding='utf8', errors="ignore") as source_file:
            content = source_file.readlines()
            existing_statement = content[line_number]
            content[line_number] = patch_code + existing_statement

    with open(source_path, 'w', encoding='utf8', errors="ignore") as source_file:
        source_file.writelines(content)


def insert_code_range(patch_code, source_path, line_number):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    content = ""
    emitter.information("inserting code at line " + str(line_number) + " in " + source_path)
    if os.path.exists(source_path):
        with open(source_path, 'r', encoding='utf8', errors="ignore") as source_file:
            content = source_file.readlines()

    updated_content = content[:line_number-1] + patch_code + content[line_number-1:]
    # print(set(updated_content) - set(content))
    with open(source_path, 'w', encoding='utf8', errors="ignore") as source_file:
        source_file.writelines(updated_content)


def delete_code(source_path, start_line, end_line):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    content = ""
    emitter.information("deleting lines " + str(start_line) + "-" + str(end_line) + " in " + source_path)
    if os.path.exists(source_path):
        with open(source_path, 'r+', encoding='utf8', errors="ignore") as source_file:
            content = source_file.readlines()
            source_file.seek(0)
            source_file.truncate()
    original_content = content
    del content[start_line-1:end_line]
    # print(set(original_content) - set(content))
    with open(source_path, 'w', encoding='utf8', errors="ignore") as source_file:
        source_file.writelines(content)


def weave_headers(missing_header_list, modified_source_list):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    if not missing_header_list:
        emitter.normal("\t-none-")
    source_file = ""
    for header_file_a in missing_header_list:
        emitter.normal(header_file_a)
        target_file = missing_header_list[header_file_a]
        header_file_c = finder.find_clone(header_file_a)
        if header_file_c:
            target_file_dir_path = "/".join(target_file.split("/")[:-1]).replace(values.Project_D.path, "")
            if target_file_dir_path[0] == "/":
                target_file_dir_path = target_file_dir_path[1:]
            header_file_dir_path = "/".join(header_file_c.split("/")[:-1])
            if header_file_dir_path[0] == "/":
                header_file_dir_path = header_file_dir_path[1:]
            if header_file_c:
                emitter.success("\t\tfound clone header file: " + header_file_c)
                header_name = header_file_c.replace(values.Project_C.path, "")
            else:
                header_name = header_file_a.replace(values.Project_A.path, "")

            if target_file_dir_path == header_file_dir_path:
                header_name = header_name.split("/")[-1]
            if header_name[0] == "/":
                header_name = header_name[1:]
        else:
            filepath = definitions.DIRECTORY_TMP + "/find_header"
            partial_path = "*/" + header_file_a
            find_file_using_path(values.Project_C.path, partial_path, filepath, None)
            with open(filepath, "r", errors='replace') as result:
                files = [path.strip() for path in result.readlines()]
            if files:
                header_name = header_file_a
            else:
                continue

        if "/" in header_name:
            transplant_code = "\n#include<" + header_name + ">\n"
        else:
            transplant_code = "\n#include \"" + header_name + "\"\n"
        def_insert_line = finder.find_definition_insertion_point(target_file)
        backup_file(target_file, FILENAME_BACKUP)
        insert_code(transplant_code, target_file, def_insert_line)
        if target_file not in modified_source_list:
            modified_source_list.append(target_file)
        backup_file_path = definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
        show_partial_diff(backup_file_path, target_file)

    # for source_file_c in modified_source_list:
    #     source_file_a = None
    #     for path_a, path_c in Values.VECTOR_MAP:
    #         if source_file_c in path_c:
    #             source_file_a = path_a.split(".c.")[0] + ".c"
    #     if source_file_a:
    #         added_header_list = Values.Project_A.header_list[source_file_a]['added']
    #         for header_name in added_header_list:
    #             Emitter.normal(header_name)
    #             target_file = source_file_c
    #             transplant_code = "\n#include<" + header_name + ">\n"
    #             def_insert_line = Finder.find_definition_insertion_point(target_file)
    #             backup_file(target_file, FILENAME_BACKUP)
    #             insert_code(transplant_code, target_file, def_insert_line)
    #             if target_file not in modified_source_list:
    #                 modified_source_list.append(target_file)
    #             backup_file_path = Definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
    #             show_partial_diff(backup_file_path, target_file)

    return modified_source_list


def weave_global_declarations(missing_var_list, modified_source_list):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    if not missing_var_list:
        emitter.normal("\t-none-")
    for var_name in missing_var_list:
        emitter.normal(var_name)
        var_info = missing_var_list[var_name]
        ast_node = var_info['ast-node']

        var_type = ast_node['children'][0]['value']
        var_name = ast_node['identifier']
        var_value = converter.get_node_value(ast_node['children'][1])

        transplant_code = var_type + " " + var_name + " = " + var_value + " ;\n"
        target_file = var_info['target-file']
        def_insert_line = finder.find_definition_insertion_point(target_file)
        backup_file(target_file, FILENAME_BACKUP)
        insert_code(transplant_code, target_file, def_insert_line)
        if target_file not in modified_source_list:
            modified_source_list.append(target_file)
        backup_file_path = definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
        show_partial_diff(backup_file_path, target_file)
        emitter.success("\tcode transplanted at " + target_file)
    return modified_source_list


def weave_definitions(missing_definition_list, modified_source_list):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    if not missing_definition_list:
        emitter.normal("\t-none-")
    for def_name in missing_definition_list:
        emitter.normal(def_name)
        macro_info = missing_definition_list[def_name]
        source_file = macro_info['source']
        target_file = macro_info['target']
        macro_def_list = extractor.extract_macro_definitions(source_file)
        def_insert_line = finder.find_definition_insertion_point(target_file)
        transplant_code = ""
        for macro_def in macro_def_list:
            if def_name in macro_def:
                if "#define" in macro_def:
                    if def_name in macro_def.split(" "):
                        transplant_code += "\n" + macro_def + "\n"

        if transplant_code == "":
            header_file = finder.find_header_file("#define " + def_name, source_file, target_file)
            # print(header_file)
            if header_file is not None:
                macro_def_list = extractor.extract_macro_definitions(header_file)
                # print(macro_def_list)
                transplant_code = ""
                for macro_def in macro_def_list:
                    if def_name in macro_def:
                        # print(macro_def)
                        if "#define " + def_name in macro_def:
                            transplant_code += "\n" + macro_def + "\n"
                            # TODO: not sure why we need this
                            # elif str(macro_def).count(def_name) == 1:
                            #     transplant_code += "\n" + macro_def + "\n"
                # TODO: check if internal functions inside macro
                if "})" in transplant_code:
                    transplant_code = "#include<" + header_file.split("include/")[-1] + ">\n" + transplant_code

                if "(" in def_name and transplant_code == "":
                    transplant_code = "#define " + def_name + "...)\n"
        if transplant_code != "":
            backup_file(target_file, FILENAME_BACKUP)
            insert_code(transplant_code, target_file, def_insert_line)
            if target_file not in modified_source_list:
                modified_source_list.append(target_file)
            backup_file_path = definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
            show_partial_diff(backup_file_path, target_file)
            emitter.success("\tcode transplanted at " + target_file)
    return modified_source_list


def weave_data_type(missing_data_type_list, modified_source_list):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    if not missing_data_type_list:
        emitter.normal("\t-none-")

    for data_type in missing_data_type_list:
        emitter.normal(data_type)
        data_type_info = missing_data_type_list[data_type]
        ast_node = data_type_info['ast-node']
        ast_node_type = ast_node['type']
        source_file = ast_node['file']
        if not os.path.isfile(source_file):
            source_file = values.Project_A.path + "/" + source_file
        def_start_line = int(ast_node['start line'])
        def_end_line = int(ast_node['end line'])
        target_file = data_type_info['target']
        transplant_code = "\n"
        if ast_node_type == "FieldDecl":
            def_insert_line = data_type_info['insert-line']
        else:
            def_insert_line = finder.find_definition_insertion_point(target_file)
        for i in range(def_start_line, def_end_line + 1, 1):
            transplant_code += get_code(source_file, int(i))
        transplant_code += "\n"
        backup_file(target_file, FILENAME_BACKUP)
        insert_code(transplant_code, target_file, def_insert_line)
        if target_file not in modified_source_list:
            modified_source_list.append(target_file)
        backup_file_path = definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
        show_partial_diff(backup_file_path, target_file)
        emitter.success("\tcode transplanted at " + target_file)
    return modified_source_list


def weave_functions(missing_function_list, modified_source_list):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    if not missing_function_list:
        emitter.normal("\t-none-")
    def_insert_point = ""
    missing_header_list = dict()
    missing_macro_list = dict()
    for function_name in missing_function_list:
        info = missing_function_list[function_name]
        node_id = info['node_id']
        source_path_a = info['source_a']
        source_path_d = info['source_d']
        emitter.normal(function_name)
        ast_tree_a = ast_generator.get_ast_json(source_path_a, regenerate=True)
        function_ref_node_id = int(info['ref_node_id'])
        function_ref_node = finder.search_ast_node_by_id(ast_tree_a, function_ref_node_id)
        function_def_node = finder.search_ast_node_by_id(ast_tree_a, int(node_id))
        function_node, function_source_file = extractor.extract_complete_function_node(function_def_node,
                                                                                       source_path_a)
        def_insert_point = finder.find_definition_insertion_point(source_path_d)

        start_line = function_node["start line"]
        end_line = function_node["end line"]
        # print(function_name)
        original_function = ""
        for i in range(int(start_line), int(end_line + 1)):
            original_statement = get_code(function_source_file, int(i))
            for data_type_a in values.data_type_map:
                data_type_c = values.data_type_map[data_type_a]
                if data_type_a in original_statement:
                    original_statement = original_statement.replace(data_type_a, data_type_c)
            original_function += original_statement + "\n"
        # translated_patch = translate_patch(original_patch, var_map_ac)
        backup_file(source_path_d, FILENAME_BACKUP)
        insert_code(original_function, source_path_d, def_insert_point)
        if source_path_d not in modified_source_list:
            modified_source_list.append(source_path_d)
        backup_file_path = definitions.DIRECTORY_BACKUP + "/" + FILENAME_BACKUP
        show_partial_diff(backup_file_path, source_path_d)
        emitter.success("\tcode transplanted at " + source_path_d)
    return modified_source_list


def weave_code(file_a, file_b, file_c, script_file_name, modified_source_list):
    # if values.DONOR_REQUIRE_MACRO:
    #     values.PRE_PROCESS_MACRO = values.DONOR_PRE_PROCESS_MACRO
    # if values.TARGET_REQUIRE_MACRO:
    #     values.PRE_PROCESS_MACRO = values.TARGET_PRE_PROCESS_MACRO

    file_d = str(file_c).replace(values.Project_C.path, values.Project_D.path)

    # Check for an edit script
    # script_file_name = Definitions.DIRECTORY_OUTPUT + "/" + str(file_index) + "_script"
    syntax_error_file_name = definitions.DIRECTORY_OUTPUT + "/" + str(file_index) + "_syntax_errors"

    file_info = file_a, file_b, file_c, file_d

    if values.DEFAULT_OPERATION_MODE in [0, 3]:
        execute_ast_transformation(script_file_name, file_info)
    elif values.DEFAULT_OPERATION_MODE in [1, 2]:
        execute_diff_transformation(script_file_name, file_info)

    # We fix basic syntax errors that could have been introduced by the patch
    fix_command = definitions.SYNTAX_CHECK_COMMAND + "-fixit " + file_d

    if file_c[-1] == 'h':
        fix_command += " --"
    fix_command += " 2>" + syntax_error_file_name
    execute_command(fix_command)

    if file_d not in modified_source_list:
        modified_source_list.append(file_d)

    emitter.success("\n\tSuccessful transformation")
    return modified_source_list


def weave_slice(slice_info):
    for source_file_d, source_file_b in slice_info:
        source_file_c = source_file_d.replace(values.Project_D.path, values.CONF_PATH_C)
        emitter.normal("\t\t" + source_file_d)
        slice_list = slice_info[(source_file_d, source_file_b)]
        weave_list = dict()
        for slice_file in slice_list:
            segment_code = slice_file.replace(source_file_d + ".", "").split(".")[0]
            segment_identifier = slice_file.split("." + segment_code + ".")[-1].replace(".slice", "")
            emitter.normal("\t\t\tweaving slice " + segment_identifier)
            segment_type = values.segment_map[segment_code]
            backup_file_orig(source_file_d)
            replace_file(slice_file, source_file_d)
            if values.TARGET_REQUIRE_MACRO:
                values.PRE_PROCESS_MACRO = values.TARGET_PRE_PROCESS_MACRO
            ast_tree_slice = ast_generator.get_ast_json(source_file_d, values.TARGET_REQUIRE_MACRO, True)
            restore_file_orig(source_file_d)
            ast_tree_source = ast_generator.get_ast_json(source_file_d, values.TARGET_REQUIRE_MACRO, True)
            segment_node_slice = finder.search_node(ast_tree_slice, segment_type, segment_identifier)
            segment_node_source = finder.search_node(ast_tree_source, segment_type, segment_identifier)
            start_line_source = int(segment_node_source['start line'])
            end_line_source = int(segment_node_source['end line'])
            if segment_node_slice:
                start_line_slice = int(segment_node_slice['start line'])
                end_line_slice = int(segment_node_slice['end line'])
                weave_list[start_line_source] = (slice_file, end_line_source, start_line_slice, end_line_slice)
            else:
                weave_list[start_line_source] = (slice_file, end_line_source, None, None)

        for start_line_source in reversed(sorted(weave_list.keys())):
            slice_file, end_line_source, start_line_slice, end_line_slice = weave_list[start_line_source]
            delete_code(source_file_d, start_line_source, end_line_source)
            if start_line_slice:
                slice_code = get_code_range(slice_file, start_line_slice, end_line_slice)
                insert_code_range(slice_code, source_file_d, start_line_source)

        source_file_a = source_file_b.replace(values.CONF_PATH_B, values.CONF_PATH_A)
        show_patch(source_file_a, source_file_b, source_file_c, source_file_d, segment_identifier)
