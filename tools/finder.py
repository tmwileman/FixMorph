#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
from ast import ast_generator, ast_vector
from tools import oracle, logger, extractor, emitter
from common.utilities import execute_command, error_exit, find_files
from common import definitions

FILE_GREP_RESULT = ""


def search_vector(file_path):
    with open(file_path, 'r', errors='replace') as vec_file:
            content = vec_file.readline()
            if content:
                vector = [int(s) for s in vec_file.readline().strip().split(" ")]
                vector = vector.Vector.normed(vector)
                return vector
            else:
                emitter.information("Vector file is empty")
    emitter.information("Vector file not found")
    return None


def search_vector_list(project, extension, vec_type):
    if "c" in extension:
        rxt = "C"
    else:
        rxt = "h"

    emitter.normal("\tanalysing vectors for " + vec_type + " segments in " + project.name + "...")
    filepath = definitions.DIRECTORY_OUTPUT + "/vectors_" + rxt + "_" + project.name
    find_files(project.path, extension, filepath, None)
    with open(filepath, "r", errors='replace') as file:
        files = [vec.strip() for vec in file.readlines()]
    vecs = []
    for i in range(len(files)):
        vecs.append((files[i], search_vector(files[i])))
    return vecs


def search_matching_node(ast_node, search_node, var_map):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    node_id = int(ast_node['id'])
    node_type = str(ast_node['type'])
    search_node_type = str(search_node['type'])
    if node_type == search_node_type:
        if oracle.is_node_equal(ast_node, search_node, var_map):
            return node_type + "(" + str(node_id) + ")"

    for child_node in ast_node['children']:
        if len(child_node['children']) > 0:
            target_node_str = search_matching_node(child_node, search_node, var_map)
            if target_node_str is not None:
                return target_node_str


def find_ast_node_position(ast_node, line_number):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    node_id = ast_node['id']
    node_type = ast_node['type']
    child_index = 0
    line_number = int(line_number)
    prev_child_node = ""
    for child_node in ast_node['children']:
        child_node_id = int(child_node['id'])
        child_node_type = str(child_node['type'])
        child_node_start_line = int(child_node['start line'])
        child_node_end_line = int(child_node['end line'])
        if child_node_start_line == line_number:
            return str(node_type) + "(" + str(node_id) + ") at " + str(child_index)
        elif child_node_start_line > line_number:
            return find_ast_node_position(prev_child_node, line_number)
        prev_child_node = child_node
        child_index += 1
    return find_ast_node_position(prev_child_node, line_number)


def search_ast_node_by_id(ast_node, find_id):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    is_high = False
    is_low = False
    prev_child_node = None
    if not ast_node:
        return None
    node_id = int(ast_node['id'])
    if node_id == find_id:
        return ast_node
    for child_node in ast_node['children']:
        child_id = int(child_node['id'])
        if child_id == find_id:
            return child_node
        elif child_id < find_id:
            is_low = True
        else:
            is_high = True

        if is_low and is_high:
            return search_ast_node_by_id(prev_child_node, int(find_id))
        else:
            prev_child_node = child_node
    return search_ast_node_by_id(prev_child_node, int(find_id))


def search_function_node_by_name(ast_node, function_name):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    function_node = None
    for child_node in ast_node['children']:
        child_node_type = child_node['type']
        if child_node_type == "FunctionDecl":
            child_node_identifier = child_node['identifier']
            # print(child_node_identifier, function_name)
            if child_node_identifier == function_name:
                function_node = child_node
    return function_node


def search_node(ast_tree, node_type, node_identifier):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    for ast_node in ast_tree['children']:
        ast_node_type = ast_node['type']
        if ast_node_type == node_type:
            ast_node_identifier = ast_node['identifier']
            # print(child_node_identifier, function_name)
            if ast_node_identifier == node_identifier:
                if node_type == "FunctionDecl":
                    if 'file' in ast_node.keys():
                        if str(ast_node['file'])[-2:] == ".h":
                            continue
                    if len(ast_node['children']) > 1:
                        if ast_node['children'][1]['type'] == "CompoundStmt":
                            return ast_node
                else:
                    return ast_node


def search_function_node_by_loc(ast_node, line_number, source_path):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    file_name = source_path.split("/")[-1]
    for child_node in ast_node['children']:
        child_node_type = child_node['type']
        if child_node_type == "FunctionDecl":
            if "file" in child_node.keys():
                function_source = child_node['file']
                if file_name not in function_source:
                    continue
            child_node_start_line = int(child_node['start line'])
            child_node_end_line = int(child_node['end line'])
            if line_number in range(child_node_start_line, child_node_end_line + 1):
                return child_node

    for child_node in ast_node['children']:
        if child_node_type == "Macro":
            child_node_start_line = int(child_node['start line'])
            child_node_end_line = int(child_node['end line'])
            if line_number in range(child_node_start_line, child_node_end_line + 1):
                return child_node
    return None


def search_node_by_loc(ast_node, line_number):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    for child_node in ast_node['children']:
        child_node_start_line = int(child_node['start line'])
        child_node_end_line = int(child_node['end line'])
        if child_node_start_line == line_number:
            return child_node
        if child_node_start_line == line_number:
            return child_node
        if line_number in range(child_node_start_line, child_node_end_line + 1):
            return search_node_by_loc(child_node, line_number)
    return None


def find_definition_insertion_point(source_path):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    file_name = source_path.split("/")[-1]
    ast_node = ast_generator.get_ast_json(source_path)
    for child_node in ast_node['children']:
        child_node_type = child_node['type']
        if child_node_type == "FunctionDecl":
            if 'file' in child_node:
                child_node_file_name = child_node['file'].split("/")[-1]
                if child_node_file_name == file_name:
                    return int(child_node['start line'])
    return 0


def find_header_file(query, source_path):
    logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    global FILE_GREP_RESULT
    project_dir = extractor.extract_project_path(source_path)
    FILE_GREP_RESULT = definitions.DIRECTORY_OUTPUT + "/grep-output"
    search_command = "cd " + project_dir + ";"
    search_command += "grep -inr -e \"" + query + "\" . | grep define"
    search_command += " > " + FILE_GREP_RESULT
    execute_command(search_command)
    with open(FILE_GREP_RESULT, 'r') as result_file:
        lines = result_file.readlines()
        if len(lines) == 1:
            relative_path = str(lines[0]).split(":")[0]
            abs_path = project_dir + "/" + relative_path
            return abs_path
        else:
            error_exit("\t\tError: more than one result for GREP")

    return None
