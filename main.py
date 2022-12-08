import os
import zlib
import string
import re

def getText(filename):
    file = open(filename, 'rb')
    text = file.read()
    file.close()
    return zlib.decompress(text)

def parseCommit(text, file_name, commitsNames):
    commit = {}
    decoded = text.decode("utf-8")
    matchName = re.search(r'\n(.+)\n*$', decoded)
    matchParent = re.search(r'parent (.+)\n', decoded)
    matchTree = re.search(r'tree (.+)\n', decoded)
    if (matchName):
        name = matchName[1]
        if (name not in commitsNames):
            commitsNames.append(name)
            if (matchParent):
                commit['parent'] = matchParent[1]
            if (matchTree):
                commit['tree'] = matchTree[1]
            commit['id'] = file_name
            commit['name'] = name
    return commit

def gitType(filePath, path):
    path = os.path.normpath(path)
    gitPath = "..\.git\objects"
    gitPath = os.path.normpath(gitPath)
    gitPath = os.path.join(path, gitPath, filePath[0:2], filePath[2:])
    return getText(gitPath).split()[0].decode("utf-8")

def parseTree(text, fileName, path):
    tree = {}
    tree["type"] = "tree"
    tree["name"] = fileName
    files = []
    byte = text.find(b'\x00')
    text = text[byte+1:]

    files = []

    while len(text):
        byte = text.find(b'\x00')
        lineName = text[0:byte].decode("utf-8").split()
        text = text[byte+1:]
        filePath = text[0:20]
        files.append({
            "type": gitType(filePath.hex(), path),
            "mode": lineName[0],
            "name": lineName[1],
            "filePath": filePath.hex()
        })
        text = text[20:]
        tree["files"] = files
    return tree

def orderCommits(commits):
    orderedCommits = []

    for cm in commits:
        if (not cm.get('parent')):
            orderedCommits.append(cm)
            break
    
    # print(orderedCommits)

    for i in range(len(commits) - 1):
        for cm in commits:
            # print(cm)
            if (cm.get('parent') and orderedCommits[-1]['name'] == cm['parent']):
                orderedCommits.append(cm)
                break

    return orderedCommits

def getNodes(commits, trees):
    nodes = []
    newCommits = []

    for cm in commits:
        newCommit = {}
        if (cm.get('parent')):
            newCommit['parent'] = cm['parent']
        newCommit['name'] = cm['name']
        newCommit['nodes'] = []
        for tree in trees:
            if (cm['tree'] == tree['name']):
                for node in tree['files']:
                    if (node['type'] == 'tree' and node not in nodes):
                        newCommit['nodes'].append({'type': 'dir', 'name': node['name'], 'nodes': []})
                        # nodes.append(node)
                        for tempTree in trees:
                            if (node['filePath'] == tempTree['name']):
                                for tempNode in tempTree['files']:
                                    if (tempNode['type'] == 'tree' and tempNode not in nodes):
                                        newCommit['nodes'][-1]['nodes'].append({'type': 'dir', 'name': tempNode['name'], 'nodes': []})
                                        # nodes.append(tempNode)
                                        for tempTree2 in trees:
                                            if (tempNode['filePath'] == tempTree2['name']):
                                                for tempNode2 in tempTree2['files']:
                                                    if (tempNode2['type'] == 'blob' and tempNode2 not in nodes):
                                                        newCommit['nodes'][-1]['nodes'][-1]['nodes'].append({'type': 'file', 'name': tempNode2['name']})
                                                        # nodes.append(tempNode2)
                                for tempNode in tempTree['files']:
                                    if (tempNode['type'] == 'blob' and tempNode not in nodes):
                                        newCommit['nodes'][-1]['nodes'].append({'type': 'file', 'name': tempNode['name']})
                                        # nodes.append(tempNode)
                for node in tree['files']:
                    if (node['type'] == 'blob' and node not in nodes):
                        newCommit['nodes'].append({'type': 'file', 'name': node['name']})
                        # nodes.append(node)
        newCommits.append(newCommit)

    return newCommits

def getCommits(path):
    gitPath = "..\.git\objects"
    gitPath = os.path.join(os.path.normpath(path), os.path.normpath(gitPath))
    gitPath = os.walk(gitPath)

    commits = []
    commitsNames = []
    trees = []

    for object in gitPath:
        if (len(object[2]) == 1):
            filePath = os.path.join(object[0], object[2][0])
            fileName = object[0][-2] + object[0][-1] + object[2][0]
            text = getText(filePath)
            type = text.split()[0].decode("utf-8")
            if type == "commit":
                commit = parseCommit(text, fileName, commitsNames)
                if (commit.get('name')):
                    commits.append(commit)
            elif type == "tree":
                tree = parseTree(text, fileName, path)
                trees.append(tree)

    for cm in commits:
        if (cm.get('parent')):
            for commit in commits:
                if (cm['parent'] == commit['id']):
                    cm['parent'] = commit['name']
                    break
    for cm in commits:
        cm.pop('id')

    # print(commits)

    commits = orderCommits(commits)
    # print(trees)
    nodes = getNodes(commits, trees)
    return nodes

def getGraph(commits = []):
    graph = "digraph Commits {\n"

    cmColor = "#ffe4c4"
    dirColor = "#56d156"
    fileColor = "#61b1e3"

    counter = 0
    for commit in commits:
        graph += f'  {counter}[label="Commit: {commit["name"]}", color="{cmColor}", shape=cylinder, style="rounded,filled"]\n'
        counter += 1
        for node in commit['nodes']:
            if (node['type'] == 'file'):
                graph += f'  {counter}[label="File: {node["name"]}", color="{fileColor}", shape=component, style="rounded,filled"]\n'
                counter += 1
            elif (node['type'] == 'dir'):
                graph += f'  {counter}[label="Directory: {node["name"]}", color="{dirColor}", shape=folder, style="rounded,filled"]\n'
                counter += 1

                for n in node['nodes']:
                    if (n['type'] == 'file'):
                        graph += f'  {counter}[label="File: {n["name"]}", color="{fileColor}", shape=component, style="rounded,filled"]\n'
                        counter += 1
                    elif (n['type'] == 'dir'):
                        graph += f'  {counter}[label="Directory: {n["name"]}", color="{dirColor}", shape=folder, style="rounded,filled"]\n'
                        counter += 1
    
                        for k in n['nodes']:
                            if (k['type'] == 'file'):
                                graph += f'  {counter}[label="File: {k["name"]}", color="{fileColor}", shape=component, style="rounded,filled"]\n'
                                counter += 1
                            elif (k['type'] == 'dir'):
                                graph += f'  {counter}[label="Directory: {k["name"]}", color="{dirColor}", shape=folder, style="rounded,filled"]\n'
                                counter += 1
    counter = 0
    commitCounter = 0
    dirCounter = 0
    prevDirCounter = 0
    for commit in commits:
        if (commit.get('parent')):
            graph += f'  {commitCounter} -> {counter}\n'
        commitCounter = counter
        counter += 1
        for node in commit['nodes']:
            if (node['type'] == 'file'):
                graph += f'  {commitCounter} -> {counter}\n'
                counter += 1
            elif (node['type'] == 'dir'):
                graph += f'  {commitCounter} -> {counter}\n'
                prevDirCounter = counter
                counter += 1
                for n in node['nodes']:
                    if (n['type'] == 'file'):
                        graph += f'  {prevDirCounter} -> {counter}\n'
                        counter += 1
                    elif (n['type'] == 'dir'):
                        graph += f'  {prevDirCounter} -> {counter}\n'
                        dirCounter = counter
                        counter += 1
                        for k in n['nodes']:
                            graph += f'  {dirCounter} -> {counter}\n'
                            counter += 1
    graph += "}"
    
    return graph

if __name__ == "__main__":
    path = os.getcwd()
    commits = getCommits(path)
    graph = getGraph(commits)
    print(graph)