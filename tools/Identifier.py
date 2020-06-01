#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
import os

from common.Utilities import error_exit, is_intersect
import collections
from common import Values
from tools import Emitter, Logger, Extractor, Finder, Oracle, Converter
from ast import Generator, Vector
from tools import Generator as Gen


STANDARD_DATA_TYPES = ["int", "char", "float", "unsigned int", "uint32_t", "uint8_t", "char *"]


def identify_missing_labels(ast_map, ast_node, source_path_b, source_path_d, skip_list):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing labels")
    missing_label_list = list()
    label_list = Extractor.extract_label_node_list(ast_node)
    return missing_label_list


def identify_missing_functions(ast_map_b, ast_node, source_path_b, source_path_d, ast_map_c):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing function calls")
    missing_function_list = dict()
    call_list = Extractor.extract_call_node_list(ast_node)
    function_list = Extractor.extract_function_node_list(ast_map_c)
    # print(call_list)
    # print(skip_list)
    for call_expr in call_list:
        # print(call_expr)
        function_ref_node = call_expr['children'][0]
        function_name = function_ref_node['value']
        # print(function_name)
        if function_name in function_list.keys():
            continue
        line_number = function_ref_node['start line']
        # print(line_number)

        function_node = Finder.search_function_node_by_name(ast_map_b, function_name)
        # print(function_node)
        if function_node is not None:
            # print(function_node)
            if function_name not in missing_function_list.keys():
                info = dict()
                info['node_id'] = function_node['id']
                info['ref_node_id'] = function_ref_node['id']
                info['source_b'] = source_path_b
                info['source_d'] = source_path_d
                missing_function_list[function_name] = info
            else:
                info = dict()
                info['node_id'] = function_node['id']
                info['ref_node_id'] = function_ref_node['id']
                info['source_b'] = source_path_b
                info['source_d'] = source_path_d
                if info != missing_function_list[function_name]:
                    print(missing_function_list[function_name])
                    error_exit("MULTIPLE FUNCTION REFERENCES ON DIFFERENT TARGETS FOUND!!!")
    # print(missing_function_list)
    return missing_function_list


def identify_missing_var(neighborhood_a, neighborhood_c, insert_node_b, source_path_b, var_map):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing variables")
    missing_var_list = dict()
    print(insert_node_b)
    ref_list = Extractor.extract_reference_node_list(insert_node_b)
    print(ref_list)
    dec_list_a = Extractor.extract_decl_node_list(neighborhood_a)
    print(dec_list_a.keys())
    dec_list_c = Extractor.extract_decl_node_list(neighborhood_c)
    print(dec_list_c.keys())
    ast_tree = Generator.get_ast_json(source_path_b)
    enum_list = Extractor.extract_enum_node_list(ast_tree)
    if insert_node_b['type'] == "Macro":
        macro_value = insert_node_b['value']
        if "(" in macro_value:
            operand_list = macro_value.split("(")[1].split(")")[0].split(",")
            for operand in operand_list:
                if operand not in dec_list_c.keys():
                    if operand not in missing_var_list.keys() and operand in dec_list_a.keys():
                        info = dict()
                        info['ref_list'] = list()
                        info['ast-node'] = dec_list_a[operand]
                        missing_var_list[operand] = info
            print(missing_var_list)
            return missing_var_list

    for ref_node in ref_list:
        node_type = str(ref_node['type'])
        node_start_line = int(ref_node['start line'])
        if node_type == "DeclRefExpr":
            if "ref_type" in ref_node.keys():
                ref_type = str(ref_node['ref_type'])
                identifier = str(ref_node['value'])
                if ref_type == "VarDecl":
                    if identifier not in dec_list_c.keys():
                        if identifier not in missing_var_list.keys() and identifier in dec_list_a.keys():
                            info = dict()
                            info['ref_list'] = list()
                            info['ast-node'] = dec_list_a[identifier]
                            missing_var_list[identifier] = info
                    elif identifier not in var_map.keys():
                        skip = False
                        for var in var_map.keys():
                            if identifier in var:
                                skip = True
                                break
                        if not skip:
                            if identifier not in missing_var_list.keys() and identifier in dec_list_a.keys():
                                info = dict()
                                info['ref_list'] = list()
                                info['ast-node'] = dec_list_a[identifier]
                                missing_var_list[identifier] = info
                elif ref_type == "FunctionDecl":
                    if identifier in Values.STANDARD_FUNCTION_LIST:
                        continue
            else:
                identifier = str(ref_node['value'])
                if identifier not in missing_var_list.keys() and identifier in enum_list.keys():
                    info = dict()
                    info['ref_list'] = list()
                    info['ast-node'] = enum_list[identifier]
                    missing_var_list[identifier] = info
    print(missing_var_list)
    return missing_var_list


def identify_missing_data_types(insert_node_b, var_info, target_path, ast_node_b, ast_node_c, source_path_b):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing data-types")
    missing_data_type_list = dict()
    type_loc_node_list = Extractor.extract_typeloc_node_list(insert_node_b)
    # print(type_loc_node_list)
    ref_list = Extractor.extract_reference_node_list(insert_node_b)
    type_def_node_list_b = Extractor.extract_typedef_node_list(ast_node_b)
    type_def_node_list_c = Extractor.extract_typedef_node_list(ast_node_c)
    for ref_node in ref_list:
        # print(ref_node)
        node_type = str(ref_node['type'])
        node_start_line = int(ref_node['start line'])
        if node_type == "DeclRefExpr":
            if "ref_type" not in ref_node.keys():
                continue
            ref_type = str(ref_node['ref_type'])
            if ref_type == "VarDecl":
                identifier = str(ref_node['data_type'])
                # print(identifier)
                var_name = str(ref_node['value'])
                # print(var_name)
                if var_name not in var_info.keys():
                    continue
                if identifier in STANDARD_DATA_TYPES:
                    continue
                # print("cont")
                if identifier not in type_def_node_list_c:
                    if identifier not in missing_data_type_list.keys():
                        info = dict()
                        info['target'] = target_path
                        ast_node = type_def_node_list_b[identifier]
                        source_file = str(ast_node['file'])
                        if ".." in source_file:
                            source_file = source_path_b + "/../" + str(ast_node['file'])
                            source_file = os.path.abspath(source_file)
                            if not os.path.isfile(source_file):
                                Emitter.warning("\t\tFile: " + str(source_file))
                                error_exit("\t\tFile Not Found!")
                        ast_node['file'] = source_file
                        info['ast-node'] = ast_node
                        missing_data_type_list[identifier] = info
    for type_loc_name in type_loc_node_list:
        # print(type_loc_name)
        type_loc_node = type_loc_node_list[type_loc_name]
        identifier = str(type_loc_node['value'])
        if identifier not in type_def_node_list_c:
            if identifier in STANDARD_DATA_TYPES:
                continue
            if identifier not in missing_data_type_list.keys():
                info = dict()
                info['target'] = target_path
                ast_node = type_def_node_list_b[identifier]
                source_file = str(ast_node['file'])
                if ".." in source_file:
                    source_file = source_path_b + "/../" + str(ast_node['file'])
                    source_file = os.path.abspath(source_file)
                    if not os.path.isfile(source_file):
                        Emitter.warning("\t\tFile: " + str(source_file))
                        error_exit("\t\tFile Not Found!")
                ast_node['file'] = source_file
                info['ast-node'] = ast_node
                missing_data_type_list[identifier] = info
    return missing_data_type_list


def identify_missing_headers(ast_node, target_file):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing headers")
    missing_header_list = dict()
    node_type = ast_node['type']
    if node_type == "FunctionDecl":
        function_definition = ast_node['value']
        function_name = ast_node['identifier']
        return_type = (function_definition.replace(function_name, "")).split("(")[1]
        if return_type.strip() == "_Bool":
            if "stdbool.h" not in missing_header_list.keys():
                missing_header_list["stdbool.h"] = target_file
            else:
                error_exit("UNKNOWN RETURN TYPE")
    else:
        data_type_list = Extractor.extract_data_type_list(ast_node)
        std_int_list = ["uint_fast32_t", "uint_fast8_t"]
        if any(x in data_type_list for x in std_int_list):
            if "stdint.h" not in missing_header_list.keys():
                missing_header_list["stdint.h"] = target_file
            else:
                error_exit("UNKNOWN RETURN TYPE")
    return missing_header_list


def identify_missing_definitions(function_node, missing_function_list):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing definitions")
    missing_definition_list = list()
    ref_list = Extractor.extract_reference_node_list(function_node)
    dec_list = Extractor.extract_decl_list(function_node)
    function_identifier = function_node['identifier']
    for ref_node in ref_list:
        node_type = str(ref_node['type'])
        if node_type == "DeclRefExpr":
            ref_type = str(ref_node['ref_type'])
            identifier = str(ref_node['value'])
            if ref_type == "VarDecl":
                if identifier not in dec_list:
                    missing_definition_list.append(identifier)
            elif ref_type == "FunctionDecl":
                if identifier in Values.STANDARD_FUNCTION_LIST:
                    continue
                if identifier not in missing_function_list:
                    print(identifier)
                    print(Values.STANDARD_FUNCTION_LIST)
                    error_exit("FOUND NEW DEPENDENT FUNCTION")
    return list(set(missing_definition_list))


def identify_missing_macros(ast_node, source_file, target_file):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tanalysing for missing macros")
    # print(ast_node)
    missing_macro_list = dict()
    node_type = str(ast_node['type'])
    target_macro_list = Converter.convert_macro_list_to_dict(Extractor.extract_macro_definitions(target_file))
    if node_type == "Macro":
        node_macro_list = Extractor.extract_macro_definition(ast_node, source_file, target_file)
        for macro_name in node_macro_list:
            if macro_name not in node_macro_list:
                missing_macro_list[macro_name] = node_macro_list[macro_name]
    else:
        macro_node_list = Extractor.extract_macro_node_list(ast_node)
        node_macro_list = dict()
        # print(macro_node_list)
        for macro_node in macro_node_list:
            node_macro_list.update(Extractor.extract_macro_definition(macro_node, source_file, target_file))
        for macro_name in node_macro_list:
            if macro_name not in node_macro_list:
                missing_macro_list[macro_name] = node_macro_list[macro_name]

    # print(missing_macro_list)
    return missing_macro_list


def identify_missing_macros_in_func(function_node, source_file, target_file):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tidentifying missing macros")
    missing_macro_list = dict()
    ref_list = Extractor.extract_reference_node_list(function_node)
    dec_list = Extractor.extract_decl_list(function_node)
    function_identifier = function_node['identifier']
    for ref_node in ref_list:
        node_type = str(ref_node['type'])
        if node_type == "Macro":
            identifier = str(ref_node['value'])
            node_child_count = len(ref_node['children'])
            if function_identifier in identifier or "(" in identifier:
                continue
            if identifier in Values.STANDARD_MACRO_LIST:
                continue
            if node_child_count:
                for child_node in ref_node['children']:
                    identifier = str(child_node['value'])
                    if identifier in Values.STANDARD_MACRO_LIST:
                        continue
                    if identifier not in dec_list:
                        if identifier not in missing_macro_list.keys():
                            info = dict()
                            info['source'] = source_file
                            info['target'] = target_file
                            missing_macro_list[identifier] = info
                        else:
                            error_exit("MACRO REQUIRED MULTIPLE TIMES!!")

            else:
                if identifier not in dec_list:
                    token_list = identifier.split(" ")
                    for token in token_list:
                        if token in ["/", "+", "-"]:
                            continue
                        if token not in dec_list:
                            if identifier not in missing_macro_list.keys():
                                info = dict()
                                info['source'] = source_file
                                info['target'] = target_file
                                missing_macro_list[token] = info
                            else:
                                error_exit("MACRO REQUIRED MULTIPLE TIMES!!")
    return missing_macro_list


def identify_insertion_points(candidate_function):

    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    insertion_point_list = collections.OrderedDict()
    function_id, function_info = candidate_function
    source_path, function_name = function_id.split(":")
    start_line = int(function_info['start-line'])
    last_line = int(function_info['last-line'])
    exec_line_list = function_info['exec-lines']
    var_map = function_info['var-map']
    # don't include the last line (possible crash line)
    best_score = 0

    target_var_list = list()
    for var_a in var_map:
        var_b = var_map[var_a]
        if "(" in var_b:
            target_var_list.append(")".join(var_b.split(")")[1:]))
        else:
            target_var_list.append(var_b)
    # print(target_var_list)
    for exec_line in exec_line_list:
        # if exec_line == last_line:
        #     continue
        if Oracle.is_declaration_line(source_path, int(exec_line)):
            continue
        Emitter.special("\t\t" + source_path + "-" + function_name + ":" + str(exec_line))
        Emitter.special("\t\t" + source_path + "-" + function_name + ":" + str(exec_line))
        available_var_list = Extractor.extract_variable_list(source_path,
                                                             start_line,
                                                             exec_line,
                                                             False)
        # print(source_path, start_line, exec_line)
        # print(available_var_list)
        unique_var_name_list = list()
        for (var_name, line_num, var_type) in available_var_list:
            if var_name not in unique_var_name_list:
                unique_var_name_list.append(var_name)

        # print(exec_line)

        score = len(list(set(unique_var_name_list).intersection(target_var_list)))
        Emitter.normal("\t\t\t\tscore: " + str(score))
        insertion_point_list[exec_line] = score
        if score > best_score:
            best_score = score
    if best_score == 0 and not Values.BACKPORT:
        print(unique_var_name_list)
        print(target_var_list)
        error_exit("no matching line")

    return insertion_point_list, best_score


def identify_divergent_point(byte_list, sym_path_info, trace_list, stack_info):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\tfinding similar location in recipient")
    length = len(sym_path_info) - 1
    count_common = len(byte_list)
    candidate_list = list()
    estimated_loc = None
    trace_list = Extractor.extract_unique_in_order(trace_list)
    # print(length)
    # for n in range(length, 0, -1):
    #     print(n)
    #     key = sym_path_info.keys()[n]
    #     print(key)
    #     sym_path_list = sym_path_info[key]
    #     # print(len(sym_path_list))
    #     for sym_path in sym_path_list:
    #         # print(sym_path)
    #         bytes_temp = Extractor.extract_input_bytes_used(sym_path)
    #         # print(byte_list)
    #         # print(bytes_temp)
    #         count = len(list(set(byte_list).intersection(bytes_temp)))
    #         print(count_common, count)
    #         if count == count_common:
    #             candidate_list.append(key)
    #             break
    #     print("finish")
    # print("FINISH")
    # TODO: not sure why it was reduced by 1
    length = len(trace_list)
    # print(trace_list)
    # print(length)
    grab_nearest = False
    # print(candidate_list)
    # print(stack_info.keys())
    # print(sym_path_info.keys())
    for n in range(0, length, 1):
        trace_loc = trace_list[n]
        # print(trace_loc)
        source_path, line_number = trace_loc.split(":")
        source_path = os.path.abspath(source_path)
        # trace_loc = source_path + ":" + str(line_number)
        trace_loc_0 = trace_loc
        trace_loc_1 = source_path + ":" + str(int(line_number) + 1)
        trace_loc_2 = source_path + ":" + str(int(line_number) - 1)
        if trace_loc_0 in sym_path_info.keys():
            sym_path_list = sym_path_info[trace_loc_0]
            # print(len(sym_path_list))
            sym_path_latest = sym_path_list[-1]
            bytes_latest = Extractor.extract_input_bytes_used(sym_path_latest)
            count_latest = len(list(set(byte_list).intersection(bytes_latest)))
            if count_latest == count_common:
                count_instant = 1
                if Values.BACKPORT:
                    return str(trace_loc_0), len(sym_path_list)
                for sym_path in sym_path_list:
                    # print(sym_path)
                    bytes_temp = Extractor.extract_input_bytes_used(sym_path)
                    # print(byte_list)
                    # print(bytes_temp)
                    count = len(list(set(byte_list).intersection(bytes_temp)))
                    # print(count_common, count)
                    if count == count_common:
                        return str(trace_loc_0), count_instant
                    else:
                        count_instant = count_instant + 1
        elif trace_loc_1 in sym_path_info.keys():
            sym_path_list = sym_path_info[trace_loc_1]
            # print(len(sym_path_list))
            sym_path_latest = sym_path_list[-1]
            bytes_latest = Extractor.extract_input_bytes_used(sym_path_latest)
            count_latest = len(list(set(byte_list).intersection(bytes_latest)))
            if count_latest == count_common:
                if Values.BACKPORT:
                    return str(trace_loc_0), len(sym_path_list)
                count_instant = 1
                for sym_path in sym_path_list:
                    # print(sym_path)
                    bytes_temp = Extractor.extract_input_bytes_used(sym_path)
                    # print(byte_list)
                    # print(bytes_temp)
                    count = len(list(set(byte_list).intersection(bytes_temp)))
                    # print(count_common, count)
                    if count == count_common:
                        return str(trace_loc), count_instant
                    else:
                        count_instant = count_instant + 1
        elif trace_loc_2 in sym_path_info.keys():
            sym_path_list = sym_path_info[trace_loc_2]
            # print(len(sym_path_list))
            sym_path_latest = sym_path_list[-1]
            bytes_latest = Extractor.extract_input_bytes_used(sym_path_latest)
            count_latest = len(list(set(byte_list).intersection(bytes_latest)))
            if count_latest == count_common:
                if Values.BACKPORT:
                    return str(trace_loc_0), len(sym_path_list)
                count_instant = 1
                for sym_path in sym_path_list:
                    # print(sym_path)
                    bytes_temp = Extractor.extract_input_bytes_used(sym_path)
                    # print(byte_list)
                    # print(bytes_temp)
                    count = len(list(set(byte_list).intersection(bytes_temp)))
                    # print(count_common, count)
                    if count == count_common:
                        return str(trace_loc), count_instant
                    else:
                        count_instant = count_instant + 1
        # if grab_nearest:
        #     # print(trace_loc)
        #     if source_path in stack_info.keys():
        #         info = stack_info[source_path]
        #         # print(info)
        #         found_in_stack = False
        #         for func_name in info:
        #             line_number_stack = info[func_name]
        #             if int(line_number_stack) == int(line_number):
        #                 found_in_stack = True
        #                 break
        #         if not found_in_stack:
        #                 estimated_loc = trace_loc
        #                 break
        #     elif ".c" in trace_loc:
        #         estimated_loc = trace_loc
        #         break
        # else:
            # if trace_loc in sym_path_info.keys():
            #     sym_path_list = sym_path_info[trace_loc]
            #     # print(len(sym_path_list))
            #     sym_path_latest = sym_path_list[-1]
            #     bytes_latest = Extractor.extract_input_bytes_used(sym_path_latest)
            #     count_latest = len(list(set(byte_list).intersection(bytes_latest)))
            #     if count_latest == count_common:
            #         count_instant = 0
            #         for sym_path in sym_path_list:
            #             # print(sym_path)
            #             bytes_temp = Extractor.extract_input_bytes_used(sym_path)
            #             # print(byte_list)
            #             # print(bytes_temp)
            #             count = len(list(set(byte_list).intersection(bytes_temp)))
            #             # print(count_common, count)
            #             if count == count_common:
            #                 return trace_loc, count_instant
            #             else:
            #                 count_instant = count_instant + 1
                    # if source_path in stack_info.keys():
                    #     # print(source_path)
                    #     info = stack_info[source_path]
                    #     for func_name in info:
                    #         line_number_stack = info[func_name]
                    #         # print(line_number, line_number_stack)
                    #         if int(line_number_stack) == int(line_number):
                    #             grab_nearest = True
                    #         else:
                    #             estimated_loc = trace_loc
                    #             return estimated_loc
                    # elif ".h" in source_path:
                    #     grab_nearest = True
                    # else:
                    #     estimated_loc = trace_loc
                    #     return estimated_loc
                    # break

    return estimated_loc, 0


def identify_fixed_errors(output_a, output_b):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    fixed_error_list = list()
    error_list_a = Extractor.extract_error_list_from_output(output_a)
    error_list_b = Extractor.extract_error_list_from_output(output_b)
    fixed_error_list = [error for error in error_list_a if error not in error_list_b]
    return list(set(fixed_error_list))


def separate_segment(project, source_file, use_macro=False):
    enum_list = list()
    function_list = list()
    macro_list = list()
    struct_list = list()
    type_def_list = list()
    def_list = list()
    decl_list = list()
    asm_list = list()

    ast_tree = Gen.generate_ast_json(source_file, use_macro)
    if not ast_tree:
        error_exit("AST Tree not built, probably compile command not found")
    source_file_pattern = [source_file, source_file.split("/")[-1], source_file.replace(project.path, '')]
    for ast_node in ast_tree['children']:
        node_type = str(ast_node["type"])
        if node_type in ["VarDecl"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    parent_id = int(ast_node['parent_id'])
                    if parent_id == 0:
                        decl_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["EnumConstantDecl", "EnumDecl"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    enum_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["Macro"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    if 'value' in ast_node.keys():
                        macro_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["TypedefDecl"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    type_def_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["RecordDecl"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    struct_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["FunctionDecl"]:
            if 'file' in ast_node.keys():
                if ast_node['file'] in source_file_pattern:
                    function_list.append((ast_node["value"], ast_node["start line"], ast_node["end line"]))
        elif node_type in ["EmptyDecl", "FileScopeAsmDecl"]:
            continue
        else:
            print(ast_node)
            error_exit("unknown node type for code segmentation: " + str(node_type))

    return enum_list, function_list, macro_list, struct_list, type_def_list, def_list, decl_list


def create_vectors(project, source_file, segmentation_list, pertinent_lines):
    Emitter.normal("\t\t\tcreating vectors for neighborhoods")
    enum_list, function_list, macro_list, \
    struct_list, type_def_list, def_list, decl_list = segmentation_list
    for function_name, begin_line, finish_line in function_list:
        function_name = "func_" + function_name.split("(")[0]
        for start_line, end_line in pertinent_lines:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                Values.IS_FUNCTION = True
                if source_file not in project.function_list.keys():
                    project.function_list[source_file] = dict()
                if function_name not in project.function_list[source_file]:
                    Emitter.success("\t\t\tFunction: " + function_name.replace("func_", ""))
                    project.function_list[source_file][function_name] = Vector.Vector(source_file, function_name,
                                                                                      begin_line, finish_line, True)

    for struct_name, begin_line, finish_line in struct_list:
        struct_name = "struct_" + struct_name.split(";")[0]
        for start_line, end_line in pertinent_lines:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                Values.IS_STRUCT = True
                if source_file not in project.struct_list.keys():
                    project.struct_list[source_file] = dict()
                if struct_name not in project.struct_list[source_file]:
                    Emitter.success("\t\t\tStruct: " + struct_name.replace("struct_", ""))
                    project.struct_list[source_file][struct_name] = Vector.Vector(source_file, struct_name,
                                                                                  begin_line, finish_line, True)

    for var_name, begin_line, finish_line in decl_list:
        var_name = "var_" + var_name.split(";")[0]
        var_type = (var_name.split("(")[1]).split(")")[0]
        var_name = var_name.split("(")[0] + "_" + var_type.split(" ")[0]
        for start_line, end_line in pertinent_lines:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                Values.IS_TYPEDEC = True
                if source_file not in project.decl_list.keys():
                    project.decl_list[source_file] = dict()
                if var_name not in project.decl_list[source_file]:
                    Emitter.success("\t\t\tVariable: " + var_name.replace("var_", ""))
                    project.decl_list[source_file][var_name] = Vector.Vector(source_file, var_name,
                                                                             begin_line, finish_line, True)

    for macro_name, begin_line, finish_line in macro_list:
        macro_name = "macro_" + macro_name
        for start_line, end_line in pertinent_lines:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                Values.IS_MACRO = True
                if source_file not in project.macro_list.keys():
                    project.macro_list[source_file] = dict()
                if macro_name not in project.macro_list[source_file]:
                    Emitter.success("\t\t\tMacro: " + macro_name.replace("macro_", ""))
                    project.macro_list[source_file][macro_name] = Vector.Vector(source_file, macro_name,
                                                                                begin_line, finish_line, True)

    count = 0
    for enum_name, begin_line, finish_line in enum_list:
        enum_name = "enum_" + enum_name.split(";")[0]
        if "anonymous" in enum_name:
            count = count + 1
            enum_name = "enum_" + str(count)
        for start_line, end_line in pertinent_lines:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                Values.IS_ENUM = True

                if source_file not in project.enum_list.keys():
                    project.enum_list[source_file] = dict()
                if enum_name not in project.enum_list[source_file]:
                    Emitter.success("\t\t\tEnum: " + enum_name.replace("enum_", ""))
                    project.enum_list[source_file][enum_name] = Vector.Vector(source_file, enum_name,
                                                                              begin_line, finish_line, True)

    return Values.IS_ENUM or Values.IS_FUNCTION or Values.IS_MACRO or Values.IS_STRUCT or Values.IS_TYPEDEC


def identify_code_segment(diff_info, project):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    grouped_line_info = dict()
    for source_loc in diff_info:
        source_file, start_line = source_loc.split(":")
        diff_line_info = diff_info[source_loc]
        if source_file not in grouped_line_info:
            grouped_line_info[source_file] = list()
        grouped_line_info[source_file].append(diff_line_info['old-lines'])

    for source_file in grouped_line_info:
        Emitter.normal("\t\t" + source_file)
        pertinent_lines = grouped_line_info[source_file]
        Values.DONOR_PRE_PROCESS_MACRO = Extractor.extract_pre_macro_list(source_file)
        segmentation_list = separate_segment(project, source_file)
        found_neighborhood = create_vectors(project, source_file, segmentation_list, pertinent_lines)
        if not found_neighborhood:
            segmentation_list = separate_segment(project, source_file, True)
            create_vectors(project, source_file, segmentation_list, pertinent_lines)
            Values.DONOR_REQUIRE_MACRO = True


def identify_definition_segment(diff_info, project):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    grouped_line_info = dict()
    for source_loc in diff_info:
        source_file, start_line = source_loc.split(":")
        diff_line_info = diff_info[source_loc]
        if source_file not in grouped_line_info:
            grouped_line_info[source_file] = list()
        grouped_line_info[source_file].append(diff_line_info['old-lines'])

    for source_file_a in grouped_line_info:
        Emitter.normal("\t\t" + source_file_a)
        source_file_b = source_file_a.replace(Values.PATH_A, Values.PATH_B)
        header_list_a = Extractor.extract_header_list(source_file_a)
        header_list_b = Extractor.extract_header_list(source_file_b)
        added_header_list = list(set(header_list_b) - set(header_list_a))
        removed_header_list = list(set(header_list_a) - set(header_list_b))
        project.header_list[source_file_a] = dict()
        project.header_list[source_file_a]['added'] = added_header_list
        project.header_list[source_file_a]['removed'] = removed_header_list
        for header_file in added_header_list:
            Emitter.success("\t\t\tAdded: " + header_file)
        for header_file in removed_header_list:
            Emitter.success("\t\t\tRemoved: " + header_file)

