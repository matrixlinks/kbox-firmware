#!/usr/bin/env python

import json
import argparse
import os

class KObjectSpec:
    def __init__(self, title):
        self.title = title
        self.properties = []

    def addProperty(self, kps):
        self.properties.append(kps)

    def accept(self, visitor):
        visitor.visitObjectSpec(self)

class KPropertySpec:
    def __init__(self, name):
        self.name = name
        self.type = ""
        self.description = ""
        self.objectSpec = None

    def accept(self, visitor):
        visitor.visitPropertySpec(self)

class KSpecParser:
    def fetchSpec(self, basePath, specUri):
        print "fetch spec for {}".format(specUri)
        fileName = specUri
        jsonPath = []

        if '#' in specUri:
            parts = specUri.split('#')
            fileName = parts[0]
            jsonPath = parts[1].split('/')
            # when jsonPath = "", split returns [ "" ]
            # when jsonPath = "/xxx/yyy", split returns [ "", "xxx", "yyy" ]
            jsonPath = jsonPath[1:]

        fullPath = os.path.join(basePath, fileName)
        spec = json.load(open(fullPath, 'r'))

        for component in jsonPath:
            if component not in spec:
                print "Error - component {} not found in {}".format(component, spec)
            spec = spec[component]

        return spec

    def parseObjectSpec(self, basePath, objectSpec):
        print "parse object in {}".format(basePath)
        kos = KObjectSpec(objectSpec['title'])

        for p in objectSpec['properties'].keys():
            kps = self.parsePropertySpec(basePath, p, objectSpec['properties'][p])
            kos.addProperty(kps)

        return kos

    def parsePropertySpec(self, basePath, propertyName, propertySpec):
        print "parseProperty {} in {}".format(propertyName, basePath)
        kps = KPropertySpec(propertyName)

        if ('$ref' in propertySpec):
            ref = self.fetchSpec(basePath, propertySpec['$ref'])
            ref.update(propertySpec)
            propertySpec = ref

        if 'description' in propertySpec:
            kps.description = propertySpec['description']
        if 'type' in propertySpec:
            kps.type = propertySpec['type']
        if kps.type == 'object':
            kps.objectSpec = self.parseObjectSpec(basePath, propertySpec)

        return kps

    def getRootKObjectSpec(self, file):
        rootSpec = self.fetchSpec(os.path.dirname(file), os.path.basename(file))
        return self.parseObjectSpec(os.path.dirname(file), rootSpec)


class KVisitor:
    def visitObjectSpec(self, kos):
        pass
    def visitPropertySpec(self, kps):
        pass

class KPrettyPrinter(KVisitor):
    def __init__(self):
        self.indentLevel = 0

    def indentedPrint(self, text):
        print "  " * self.indentLevel + text

    def visitObjectSpec(self, kos):
        self.indentedPrint(kos.title)

        self.indentLevel = self.indentLevel + 1
        for p in kos.properties:
            p.accept(self)
        self.indentLevel = self.indentLevel - 1


    def visitPropertySpec(self, kps):
        self.indentedPrint("- " + kps.name + " : " + kps.type + " (" + kps.description + ")")
        if kps.objectSpec != None:
            kps.objectSpec.accept(self)




def main():
    parser = argparse.ArgumentParser("Generates C++ code from SignalK JSON specification")
    parser.add_argument("spec", help="vessel.json file")
    args = parser.parse_args()

    ksp = KSpecParser().getRootKObjectSpec(args.spec)

    kpp = KPrettyPrinter()
    kpp.visitObjectSpec(vesselSpec)


if __name__ == '__main__':
    main()
