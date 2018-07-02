#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 10:25:58 2018

@author: pedrobw
"""

import sys
import time
from Utils import exec_com, err_exit, find_files, clean, get_extensions
import Project
import Print
import ASTVector
import ASTgen
import gumtreeASTparser

Pa = None
Pb = None
Pc = None
start = -1

def initialize():
    global Pa, Pb, Pc
    with open('crochet.conf', 'r', errors='replace') as file:
        args = [i.strip() for i in file.readlines()]
    if (len(args) < 3):
        err_exit("Insufficient arguments: Pa, Pb, Pc source paths required.",
                 "Try running:", "\tpython3 ASTcrochet.py $Pa $Pb $Pc")
    Pa = Project.Project(args[0], "Pa")
    Pb = Project.Project(args[1], "Pb")
    Pc = Project.Project(args[2], "Pc")
    clean()


def find_diff_files():
    global Pa, Pb
    extensions = get_extensions(Pa.path, "output/files1")
    extensions = extensions.union(get_extensions(Pb.path, "output/files2"))
    with open('output/exclude_pats', 'w', errors='replace') as exclusions:
        for pattern in extensions:
            exclusions.write(pattern + "\n")
    c = "diff -ENBbwqr " + Pa.path + " " + Pb.path + \
        " -X output/exclude_pats | grep -P '\.c and ' > output/diff"
    exec_com(c, False)

    
def gen_diff():
    global Pa, Pb
    nums = "0123456789"
    Print.blue("Finding differing files...")
    find_diff_files()
    
    Print.blue("Starting fine-grained diff...\n")
    with open('output/diff', 'r', errors='replace') as diff:
        diff_line = diff.readline().strip()
        while diff_line:
            diff_line = diff_line.split(" ")
            file_a = diff_line[1]
            file_b = diff_line[3]
            c = "diff -ENBbwr " + file_a + " " + file_b + " > output/file_diff"
            exec_com(c, False)
            pertinent_lines = []
            pertinent_lines_b = []
            with open('output/file_diff', 'r', errors='replace') as file_diff:
                file_line = file_diff.readline().strip()
                while file_line:
                    # In file_diff, line starts with a number, <, >, or -.
                    if file_line[0] in nums:
                        # change (delete + add)
                        if 'c' in file_line:
                            l = file_line.split('c')
                        elif 'd' in file_line:
                            l = file_line.split('d')
                        elif 'a' in file_line:
                            l = file_line.split('a')
                        # range for file_a
                        a = l[0].split(',')
                        start_a = int(a[0])
                        end_a = int(a[-1])
                        # range for file_b
                        b = l[1].split(',')
                        start_b = int(b[0])
                        end_b = int(b[-1])
                        # Pertinent lines in file_a
                        pertinent_lines.append((start_a, end_a))
                        pertinent_lines_b.append((start_b, end_b))
                    file_line = file_diff.readline().strip()
            try:
                Print.blue("\tProject Pa...")
                ASTgen.find_affected_funcs(Pa, file_a, pertinent_lines)
                Print.blue("")
                Print.blue("\tProject Pb...")
                ASTgen.find_affected_funcs(Pb, file_b, pertinent_lines)
            except Exception as e:
                err_exit(e, "HERE")
                        
            diff_line = diff.readline().strip()

    
    
def gen_ASTs():
    # Generates an AST file for each .c file
    find_files(Pc.path, "*.c", "output/Cfiles")
    with open("output/Cfiles", 'r', errors='replace') as files:
        file = files.readline().strip()
        while file:
            # Parses it to remove useless information (for us) and gen vects
            try:
                ASTgen.parseAST(file, Pc)
            except Exception as e:
                err_exit(e, "Unexpected error in parseAST with file:", file)
            file = files.readline().strip()

    
def get_vector_list(src_path, filepath):
    find_files(src_path, "*.vec", filepath)
    with open(filepath, "r", errors='replace') as file:
        files = [vec.strip() for vec in file.readlines()]
    vecs = []
    for i in range(len(files)):
        with open(files[i], 'r', errors='replace') as vec:
            fl = vec.readline()
            if fl:
                v = [int(s) for s in vec.readline().strip().split(" ")]
                v = ASTVector.ASTVector.normed(v)
                vecs.append((files[i],v))
    return vecs
                
    
def compare():
    global Pa, Pc
    Print.blue("Getting vectors for Pa...")
    vecs_A = get_vector_list(Pa.path, "output/output_A")
    Print.blue("Getting vectors for Pc...")
    vecs_C = get_vector_list(Pc.path, "output/output_C")
    
    Print.blue("Variable mapping...\n")
    to_patch = []
    for i in vecs_A:
        best = vecs_C[0]
        best_d = ASTVector.ASTVector.dist(i[1], best[1])
        for j in vecs_C:
            d = ASTVector.ASTVector.dist(i[1],j[1])
            if d < best_d:
                best = j
                best_d = d
        # We go up to -4 to remove the ".vec" part
        fa = i[0].replace(Pa.path, "")[:-4].split(".")
        f_a = fa[-1]
        file_a = ".".join(fa[:-1])
        fc = best[0].replace(Pc.path, "")[:-4].split(".")
        f_c = fc[-1]
        file_c = ".".join(fc[:-1])
        # TODO: Get all pertinent matches (at dist d' < k*best_d) (with k=2?)
        Print.blue("\tBest match for " + f_a +" in $Pa/" + file_a + ":")
        Print.blue("\t\tFunction: " + f_c + " in $Pc/" + file_c)
        Print.blue("\t\tDistance: " + str(best_d) + "\n")
        Print.blue("\tVariable mapping from " + f_a + " to " + f_c + ":")
        try:
            var_map = detect_matching_variables(f_a, file_a, f_c, file_c)
        except Exception as e:
            err_exit(e, "Unexpected error while matching variables.")
        with open('output/var-map', 'r', errors='replace') as mapped:
            mapping = mapped.readline().strip()
            while mapping:
                Print.grey("\t\t" + mapping)
                mapping = mapped.readline().strip()
        to_patch.append((Pa.funcs[Pa.path + file_a][f_a],
                         Pc.funcs[Pc.path + file_c][f_c], var_map))
    return to_patch
    
def path_exception():
    m = "ValueError Exception: Incorrect directory path"
    return ValueError(m)    
    
    
def longestSubstringFinder(string1, string2):
    answer = ""
    maxlen = min(len(string1), len(string2))
    i = 0
    while i < maxlen:
        if string1[i] != string2[i]:
            break
        answer += string1[i]
        i += 1
    return answer
    
def generate_ast_map(source_a, source_b):
    common_path = longestSubstringFinder(source_a, source_b).split("/")[:-1]
    common_path = "/".join(common_path)
    ast_diff_command = "gumtree diff " + source_a + " " + source_b + \
                        " | grep -P 'Match GenericString: [A-Za-z0-9_]*\('" + \
                        " > output/ast-map "
    exec_com(ast_diff_command, False)
    

def detect_matching_variables(f_a, file_a, f_c, file_c):
    
    try:
        generate_ast_map(Pa.path + "/" + file_a, Pc.path + "/" + file_c)
    except Exception as e:
        err_exit(e, "Unexpected error in generate_ast_map.")
    function_a = Pa.funcs[Pa.path + file_a][f_a]
    variable_list_a = function_a.variables + function_a.params
    #Print.white(variable_list_a)
    while '' in variable_list_a:
        variable_list_a.remove('')
        
    a_names = [i.split(" ")[-1] for i in variable_list_a]
        
    function_c = Pc.funcs[Pc.path + file_c][f_c]
    variable_list_c = function_c.variables + function_c.params
    #Print.white(variable_list_c)
    while '' in variable_list_c:
        variable_list_c.remove('')
    
    ast_map = dict()
    try:
        with open("output/ast-map", "r", errors='replace') as ast_map_file:
            map_line = ast_map_file.readline().strip()
            while map_line:
                aux = map_line.split(" to ")
                var_a = aux[0].split("(")[0].split(" ")[-1]
                var_c = aux[1].split("(")[0].split(" ")[-1]
                if var_a in a_names:
                    if var_a not in ast_map:
                        ast_map[var_a] = dict()
                    if var_c in ast_map[var_a]:
                        ast_map[var_a][var_c] += 1
                    else:
                        ast_map[var_a][var_c] = 1
                map_line = ast_map_file.readline().strip()
    except Exception as e:
        err_exit(e, "Unexpected error while parsing ast-map")

    variable_mapping = dict()
    try:
        while variable_list_a:
            var_a = variable_list_a.pop()
            if var_a not in variable_mapping.keys():
                a_name = var_a.split(" ")[-1]
                if a_name in ast_map.keys():
                    max_match = -1
                    best_match = None
                    for var_c in ast_map[a_name].keys():
                        if max_match == -1:
                            max_match = ast_map[a_name][var_c]
                            best_match = var_c
                        elif ast_map[a_name][var_c] > max_match:
                            max_match = ast_map[a_name][var_c]
                            best_match = var_c
                    if best_match:
                        for var_c in variable_list_c:
                            c_name = var_c.split(" ")[-1]
                            if c_name == best_match:
                                variable_mapping[var_a] = var_c
                if var_a not in variable_mapping.keys():
                    variable_mapping[var_a] = "UNKNOWN"
    except Exception as e:
        err_exit(e, "Unexpected error while matching vars.")

    try:
        with open("output/var-map", "w", errors='replace') as var_map_file:
            for var_a in variable_mapping.keys():
                var_map_file.write(var_a + " -> " + variable_mapping[var_a] + "\n")
    except Exception as e:
        err_exit(e, "ASdasdas")
    
    return variable_mapping
    

def gen_func_file(ast_vec_func, output_file):
    start = ast_vec_func.start
    end = ast_vec_func.end
    Print.blue("\t\tStart line: " + str(start))
    Print.blue("\t\tEnd line: " + str(end))
    
    with open(output_file, 'w') as temp:
        with open(ast_vec_func.file, 'r', errors='replace') as file:
            ls = file.readlines()
            while start > 0:
                j = start-1
                if "}" in ls[j] or "#include" in ls [j] or ";" in ls[j] or "*/" in ls[j]:
                    break
                start = j
            temp.write("".join(ls[start:end]))
            

def gen_temp_files(vec_f, proj, ASTlists):
    Print.blue("\tFunction " + vec_f.function + "in " + proj.name + "...")
    temp_file = "output/temp_" + proj.name + ".c"
    gen_func_file(vec_f, temp_file)
    Print.blue("Gumtree parse " + vec_f.function + " in " + proj.name + "...")
    gum_file = "output/gumtree_" + proj.name
    c = "gumtree parse " + temp_file + " > " + gum_file
    exec_com(c, False)
    # This thing is recursive: depth problem...
    sys.setrecursionlimit(100000)
    ASTlists[proj.name] = gumtreeASTparser.AST_from_file(gum_file)
    sys.setrecursionlimit(1000)
    
def clean_parse(content, separator):
    if content.count(separator) == 1:
        return content.split(separator)
    i = 0
    while i < len(content):
        if content[i] == "\"":
            i += 1
            while i < len(content)-1:
                if content[i] == "\\":
                    i += 2
                elif content[i] == "\"":
                    i += 1
                    break
                else:
                    i += 1
            prefix = content[:i]
            rest = content[i:].split(separator)
            node1 = prefix + rest[0]
            node2 = separator.join(rest[1:])
            return [node1, node2]
        i += 1
    # If all the above fails (it shouldn't), hope for some luck:
    nodes = content.split(separator)
    half = len(nodes)//2
    node1 = separator.join(nodes[:half])
    node2 = separator.join(nodes[half:])
    return [node1, node2]
    
    
def transplantation(to_patch):
    
    UPDATE = "Update"
    MOVE = "Move"
    INSERT = "Insert"
    DELETE = "Delete"
    MATCH = "Match"
    TO = " to "
    AT = " at "
    INTO = " into "
    
    for (vec_f_a, vec_f_c, var_map) in to_patch:
        
        vec_f_b_file = vec_f_a.file.replace(Pa.path, Pb.path)
        vec_f_b = Pb.funcs[vec_f_b_file][vec_f_a.function]
        ASTlists = dict()
        
        Print.blue("Generating temp files for each pertinent function...")
        
        gen_temp_files(vec_f_a, Pa, ASTlists)
        gen_temp_files(vec_f_b, Pb, ASTlists)
        gen_temp_files(vec_f_c, Pc, ASTlists)
        
        Print.blue("Generating edit script from Pa to Pb...")
        exec_com("gumtree diff output/temp_Pa.c output/temp_Pb.c > " + \
                 "output/diff_script_AB", False)
                 
        Print.blue("Finding common structures in Pa with respect to Pc...")
        exec_com("gumtree diff output/temp_Pa.c output/temp_Pc.c | " + \
                 "grep 'Match ' >  output/diff_script_AC", False)        
                      
        Print.blue("Generating edit script from Pc to Pd...")

        instruction_AB = list()
        match_BA = dict()
        with open('output/diff_script_AB', 'r', errors='replace') as script_AB:
            line = script_AB.readline().strip()
            while line:
                line = line.split(" ")
                instruction = line[0]
                content = " ".join(line[1:])
                # Match node_A to node_B
                if instruction == MATCH:
                    try:
                        nodeA, nodeB = clean_parse(content, TO)
                        match_BA[nodeB] = nodeA
                    except Exception as e:
                        err_exit(e, "Something went wrong in MATCH (AB).",
                                 line, instruction, content)
                # Update node_A to label
                elif instruction == UPDATE:
                    try:
                        nodeA, label = clean_parse(content, TO)
                        instruction_AB.append((instruction, nodeA, label))
                    except Exception as e:
                        err_exit(e, "Something went wrong in UPDATE.")
                elif instruction == DELETE:
                    try:
                        nodeA = content
                        instruction_AB.append((instruction, nodeA))
                    except Exception as e:
                        err_exit(e, "Something went wrong in DELETE.")
                elif instruction == MOVE:
                    try:
                        nodeA, nodeB = clean_parse(content, INTO)
                        nodeB_at = nodeB.split(AT)
                        nodeB = AT.join(nodeB_at[:-1])
                        pos = nodeB_at[-1]
                        instruction_AB.append((instruction, nodeA, nodeB, pos))
                    except Exception as e:
                        err_exit(e, "Something went wrong in DELETE.")
                elif instruction == INSERT:
                    try:
                        nodeB1, nodeB2 = clean_parse(content, INTO)
                        nodeB2_at = nodeB2.split(AT)
                        nodeB2 = AT.join(nodeB2_at[:-1])
                        pos = nodeB2_at[-1]
                        instruction_AB.append((instruction, nodeB1, nodeB2,
                                              pos))
                    except Exception as e:
                        err_exit(e, "Something went wrong in INSERT.")
                line = script_AB.readline().strip()
                
        match_AC = dict()
        with open('output/diff_script_AC', 'r', errors='replace') as script_AC:
            line = script_AC.readline().strip()
            while line:
                line = line.split(" ")
                instruction = line[0]
                content = " ".join(line[1:])
                if instruction == MATCH:
                    try:
                        nodeA, nodeC = clean_parse(content, TO)
                        match_AC[nodeA] = nodeC
                    except Exception as e:
                        err_exit(e, "Something went wrong in MATCH (AC).",
                                 line, instruction, content)
                line = script_AC.readline().strip()
        
        instruction_CD = list()
        for i in instruction_AB:
            instruction = i[0]
            # Update nodeA to label -> Update nodeC to label
            if instruction == UPDATE:
                nodeA = i[1]
                label = i[2]
                nodeC = "?"
                if nodeA in match_AC.keys():
                    nodeC = match_AC[nodeA]
                    nodeC = nodeC.split("(")[-1][:-1]
                    nodeC = ASTlists["Pc"][int(nodeC)]
                # TODO: else?
                instruction_CD.append((UPDATE, nodeC, label))
                #print(UPDATE + " " + str(nodeC) + TO + label)
            # Delete nodeA -> Delete nodeC
            elif instruction == DELETE:
                nodeA = i[1]
                nodeC = "?"
                if nodeA in match_AC.keys():
                    nodeC = match_AC[nodeA]
                    nodeC = nodeC.split("(")[-1][:-1]
                    nodeC = ASTlists["Pc"][int(nodeC)]
                # TODO: else?
                instruction_CD.append((DELETE, nodeC))
                #print(DELETE + " " + str(nodeC))
            # TODO: pos could be different! Context! Need to get children :(
            # Move nodeA to nodeB at pos -> Move nodeC to nodeD at pos
            elif instruction == MOVE:
                nodeA = i[1]
                nodeB = i[2]
                pos = i[3]
                nodeC = "?"
                nodeD = nodeB
                if "(" in nodeD:
                    nodeD = nodeD.split("(")[-1][:-1]
                    nodeD = ASTlists["Pb"][int(nodeD)]
                if nodeA in match_AC.keys():
                    nodeC = match_AC[nodeA]
                    if "(" in nodeC:
                        nodeC = nodeC.split("(")[-1][:-1]
                        nodeC = ASTlists["Pc"][int(nodeC)]
                    if nodeB in match_BA.keys():
                        nodeA2 = match_BA[nodeB]
                        if nodeA2 in match_AC.keys():
                            nodeD = match_AC[nodeA2]
                            if "(" in nodeD:
                                nodeD = nodeD.split("(")[-1][:-1]
                                nodeD = ASTlists["Pc"][int(nodeD)]
                # TODO: else?
                instruction_CD.append((MOVE, nodeC, nodeD, pos))
                #print(MOVE + " " + str(nodeC) + INTO + str(nodeD) + AT + pos)
            # TODO: pos could be different! Context! Need to get children :(
            # Insert nodeB1 to nodeB2 at pos -> Insert nodeD1 to nodeD2 at pos
            elif instruction == INSERT:
                nodeB1 = i[1]
                nodeB2 = i[2]
                pos = i[3]
                nodeD1 = nodeB1
                if "(" in nodeD1:
                    nodeD1 = nodeD1.split("(")[-1][:-1]
                    nodeD1 = ASTlists["Pb"][int(nodeD1)]
                nodeD2 = nodeB2
                if "(" in nodeD2:
                    nodeD2 = nodeD2.split("(")[-1][:-1]
                    nodeD2 = ASTlists["Pb"][int(nodeD2)]
                if nodeB1 in match_BA.keys():
                    nodeA1 = match_BA[nodeB1]
                    if nodeA1 in match_AC.keys():
                        nodeD1 = match_AC[nodeA1]
                        if "(" in nodeD1:
                            nodeD1 = nodeD1.split("(")[-1][:-1]
                            nodeD1 = ASTlists["Pc"][int(nodeD1)]
                if nodeB2 in match_BA.keys():
                    nodeA2 = match_BA[nodeB2]
                    if nodeA2 in match_AC.keys():
                        nodeD2 = match_AC[nodeA2]
                        if "(" in nodeD2:
                            nodeD2 = nodeD2.split("(")[-1][:-1]
                            nodeD2 = ASTlists["Pc"][int(nodeD2)]
                instruction_CD.append((INSERT, nodeD1, nodeD2, pos))
                #print(INSERT + " " + str(nodeD1) + INTO + str(nodeD2) + AT + \
                #      pos)
        for i in instruction_CD:
            print(" ".join([str(j) for j in i]))
            
def safe_exec(function, title, *args):
    Print.title("Starting " + title + "...")
    descr = title[0].lower() + title[1:]
    try:
        if not args:
            a = function()
        else:
            a = function(*args)
        runtime = str(time.time() - start)
        Print.rose("Successful " + descr + ", after " + runtime + " seconds.")
    except Exception as e:
        err_exit(e, "Unexpected error during " + descr + ".")
    return a
                    
def run_crochet():
    global Pa, Pb, Pc, start
    # Little crochet introduction
    Print.start()
    
    # Time for final running time
    start = time.time()
    
    # Prepare projects directories by getting paths and cleaning residual files
    safe_exec(initialize, "projects initialization and cleaning")
    
    # Generates vectors for pertinent functions (modified from Pa to Pb)
    safe_exec(gen_diff, "search for affected functions and vector generation")
              
    # Generates vectors for all functions in Pc
    safe_exec(gen_ASTs, "vector generation for functions in Pc")

    # Pairwise vector comparison for matching
    to_patch = safe_exec(compare, "pairwise vector comparison for matching")
    
    # Using all previous structures to transplant patch
    safe_exec(transplantation, "patch transplantation", to_patch)
    
    # Final clean
    Print.title("Cleaning residual files generated by Crochet...")
    
    # Final running time and exit message
    runtime = str(time.time() - start)
    Print.exit_msg(runtime)
    
    
if __name__=="__main__":
    #test_parsing()
    try:
        run_crochet()
    except KeyboardInterrupt as e:
        err_exit("Program Interrupted by User")