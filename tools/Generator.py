#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from common.Utilities import execute_command, error_exit, find_files, get_file_extension_list
from tools import Emitter, Logger
from ast import Vector, Parser, Generator as ASTGenerator
from common.Utilities import error_exit, clean_parse


def generate_vectors(file_extension, log_file, project):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\tgenerating vectors for " + file_extension + " files in " + project.name + "...")
    # Generates an AST file for each file of extension ext

    find_files(project.path, file_extension, log_file)
    with open(log_file, 'r') as file_list:
        source_file = file_list.readline().strip()
        while source_file:
            # Parses it to get useful information and generate vectors
            try:
                function_list, definition_list = ASTGenerator.parse_ast(source_file, use_deckard=True)
                for function_name, begin_line, finish_line in function_list:
                    if source_file not in project.function_list.keys():
                        project.function_list[source_file] = dict()

                    if function_name not in project.function_list[source_file]:
                        project.function_list[source_file][function_name] = Vector.Vector(source_file, function_name,
                                                                                      begin_line, finish_line, False)

                    ASTGenerator.get_vars(project, source_file, definition_list)

            except Exception as e:
                error_exit(e, "Unexpected error in parseAST with file:", source_file)
            source_file = file_list.readline().strip()


def generate_project(project, source_file, pertinent_lines):
    Logger.trace(__name__ + ":" + sys._getframe().f_code.co_name, locals())
    Emitter.normal("\t\t" + project.path + ":")
    function_list = dict()
    definition_list = dict()
    try:
        function_list, definition_list = parse_ast(source_file, False)
    except Exception as e:
        error_exit(e, "Error in parse_ast.")

    for start_line, end_line in pertinent_lines:
        for function_name, begin_line, finish_line in function_list:
            if is_intersect(begin_line, finish_line, start_line, end_line):
                if source_file not in project.function_list.keys():
                    project.function_list[source_file] = dict()

                if function_name not in project.function_list[source_file]:
                    project.function_list[source_file][function_name] = Vector.Vector(source_file, function_name,
                                                                                     begin_line, finish_line, True)
                    Emitter.normal(
                        "\t\t\t" + function_name + " in " + source_file.replace(project.path, project.name + "/"))
                    Emitter.normal("\t\t\t" + function_name + " " + str(begin_line) + "-" + str(finish_line), False)
                break

    get_vars(project, source_file, definition_list)
    return function_list, definition_list