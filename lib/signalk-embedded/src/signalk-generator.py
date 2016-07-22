#!/usr/bin/env python

import json
import argparse
import os

class JSONSchema:
    """
    Reads a JSON Schema starting by one file and reading the referenced schema as needed.
    """

    def getSchema(self, schemaUri, cwd = None):
        """
        Returns the JSON Schema for a given path.

        :argument schemaUri: A string containing a filename and a path separated by a '#'.
        Either of them can be empty but not both at the same time. For example: schema.json#car
        :argument cwd: Optional path to use when interpreting file locations.
        """
        print "Get Schema: {}".format(schemaUri)
        (filename, objectPath) = self.parseUri(schemaUri)

        if cwd is not None:
            filename = os.path.join(cwd, filename)

        schema = self.readSchema(filename)
        objectSchema = self.findObjectInSchema(schema, objectPath)
        objectSchema = self._resolveRefs(objectSchema, filename, schema)

        # print "Schema: {}\n{}".format(schemaUri, objectSchema)
        return objectSchema

    def parseUri(self, uri):
        """
        Parses a schema URI.

        :return: a tuple (filename, objectPath) where filename is a string and can be empty
        and objectPath is a list (which can also be empty).
        """
        if '#' in uri:
            parts = uri.split('#')
            filename = parts[0]
            objectPath = parts[1].split('/')
            # when jsonPath = "", split returns [ "" ]
            # when jsonPath = "/xxx/yyy", split returns [ "", "xxx", "yyy" ]
            objectPath = objectPath[1:]
            return (filename, objectPath)
        else:
            return (uri, [])

    def readSchema(self, schemaFile):
        """
        Reads a json file and returns its content.
        """
        print "Opening {}".format(schemaFile)
        return json.load(open(schemaFile, 'r'))

    def findObjectInSchema(self, schema, objectPath):
        for component in objectPath:
            if component not in schema:
                raise KeyError("Error: Component {} not found in {} (full path was: {})".
                        format(component, schema, objectPath))
            schema = schema[component]

        return schema

    def _resolveRefs(self, schema, referringFile, referringSchema):
        """
        Resolve all references in a block of schema.

        This means walking the schema and looking for any object with $ref in them. They will
        be replaced by their definition.

        :argument schema: the schema in which to resolve $refs.
        :argument referringFile: the full path of the file used to read schema (to resolve references
        to other files)
        :argument referringSchema: the schema in which the reference was found (to resolve
        local references).
        """
        if isinstance(schema, dict):
            if '$ref' in schema:
                (filename, objectPath) = self.parseUri(schema['$ref'])
                if filename == "":
                    # resolve local dependencies
                    ref = self.findObjectInSchema(referringSchema, objectPath)
                else:
                    # If not a local dependency, load the schema normally
                    # note that this will break on circular dependencies.
                    ref = self.getSchema(schema['$ref'], os.path.dirname(referringFile))

                if '$ref' in ref:
                    raise ValueError("Referred object is a reference itself. Not supported. {}".format(ref))

                ref.update(schema)
                schema = ref
                del schema['$ref']

            for key, item in schema.items():
                schema[key] = self._resolveRefs(schema[key], referringFile, referringSchema)

            return schema
        elif isinstance(schema, list):
            newschema = []
            for item in schema:
                newschema.append(self._resolveRefs(item, referringFile, referringSchema))
            return newschema
        else:
            return schema

class KSpec(object):
    def __init__(self):
        self.title = None
        self.description = None

    def accept(self, visitor):
        pass

class KObjectSpec(KSpec):
    """
    A KObject is an element that can be instantiated by itself.
    """

    def __init__(self):
        super(KObjectSpec, self).__init__()
        self.properties = {}
        self.patternProperties = {}

    def addProperty(self, name, property):
        self.properties[name] = property

    def addPatternProperty(self, pattern, property):
        self.patternProperties[pattern] = property

    def accept(self, visitor):
        visitor.visitObject(self)

class KArraySpec(KSpec):
    """
    A KArraySpec is an array of KSpec.
    """

    def __init__(self):
        super(KArraySpec, self).__init__()
        self.items = None

    def accept(self, visitor):
        visitor.visitArray(self)

class KScalarSpec(KSpec):
    def __init__(self):
        super(KScalarSpec, self).__init__()
        self.type = None
        self.units = None
        self.example = None

    def accept(self, visitor):
        visitor.visitScalar(self)

class KSchemaParser:
    """
    Parses the SignalK JSON schema and builds a specification for objects that will
    match the spec.
    """
    def parseSchema(self, jsonSchema):
        spec = None
        type = None
        if 'type' in jsonSchema:
            type = jsonSchema['type']

        if type is None:
            print "Unable to parse this schema element because type is unknown: \n{}".format(jsonSchema)
        if isinstance(type, list):
            print "Unable to partse this schema element because they type is defined as a list. Make a choice!"
            "\n{}".format(jsonSchema)
        elif type == 'object':
            spec = KObjectSpec()
            spec = self.parseObjectSchema(spec, jsonSchema)
        elif type == 'array':
            spec = KArraySpec()
            spec = self.parseArraySchema(spec, jsonSchema)
        else:
            spec = KScalarSpec()
            spec = self.parseScalarSchema(spec, jsonSchema)

        return spec

    """
    """
    def parseCommonSchema(self, spec, jsonSchema):
        if 'allOf' in jsonSchema:
            print "Adding all of: {}".format(jsonSchema['allOf'])
            for schema in jsonSchema['allOf']:
                if isinstance(spec, KObjectSpec):
                    spec = self.parseObjectSchema(spec, schema)
                elif isinstance(spec, KArraySpec):
                    spec = self.parseArraySchema(spec, schema)
                elif isinstance(spec, KScalarSpec):
                    spec = self.parseScalarSchema(spec, schema)
                else:
                    raise TypeError("Unknown type: {}".format(spec))

        if 'anyOf' in jsonSchema:
            print "WARNING: 'anyOf' found in {} - You will have to help me decide which of the"
            "available option to use!".format(spec.title)

        if 'title' in jsonSchema:
            spec.title = jsonSchema['title']

        if 'description' in jsonSchema:
            spec.description = jsonSchema['description']

        return spec

    """
    Parses the schema definition of an array into a KArraySpec.
    """
    def parseArraySchema(self, spec, jsonSchema):
        spec = self.parseCommonSchema(spec, jsonSchema)
        if 'items' not in jsonSchema:
            raise ValueError("Missing a 'items' entry to describe schema for array items in {}".format(jsonSchema))
        if not isinstance(jsonSchema['items'], dict):
            raise ValueError("'items' should be a dict in {} - if it's an array, it uses unsupported tuple format".format(jsonSchema))

        itemSpec = self.parseSchema(jsonSchema['items'])
        spec.items = itemSpec
        return spec

    """"
    Parses the schema definition of an object into a KObjectSpec.
    """
    def parseObjectSchema(self, spec, jsonSchema):
        #print "Parsing object spec: {}".format(jsonSchema)
        spec = self.parseCommonSchema(spec, jsonSchema)
        if 'properties' in jsonSchema:
            for pName in jsonSchema['properties'].keys():
                print "Spec of {} - Parsing property {}".format(spec.title, pName)
                property = self.parseSchema(jsonSchema['properties'][pName])
                spec.addProperty(pName, property)

        if 'patternProperties' in jsonSchema:
            for pattern in jsonSchema['patternProperties'].keys():
                print "Spec of {} - Parsing patternProperty {}".format(spec.title, pattern)
                property = self.parseSchema(jsonSchema['patternProperties'][pattern])
                spec.addPatternProperty(pattern, property)

        return spec

    def parseScalarSchema(self, spec, jsonSchema):
        spec = self.parseCommonSchema(spec, jsonSchema)
        spec.type = jsonSchema['type']

        if 'example' in jsonSchema:
            spec.example = jsonSchema['example']
        if 'units' in jsonSchema:
            spec.units = jsonSchema['units']
        if 'enum' in jsonSchema:
            #TODO: parse enum values
            pass

        return spec

class KVisitor:
    def visit(self, k):
        k.accept(self)

    def visitObject(self, k):
        pass
    def visitArray(self, k):
        pass
    def visitScalar(self, k):
        pass

class KPrettyPrinter(KVisitor):
    def __init__(self):
        self.indentLevel = 0

    def indentedPrint(self, text):
        print "  " * self.indentLevel + text

    def indentPush(self):
        self.indentLevel = self.indentLevel + 1

    def indentPop(self):
        self.indentLevel = self.indentLevel - 1

    def visitObject(self, ks):
        self.indentedPrint("object {}: {}".format(ks.title, ks.description))

        self.indentPush()
        for (pattern, p) in ks.patternProperties.items():
            self.indentedPrint("- " + pattern + " : ")
            self.indentPush()
            p.accept(self)
            self.indentPop()

        for (name, p) in ks.properties.items():
            self.indentedPrint("- " + name + " : ")
            self.indentPush()
            p.accept(self)
            self.indentPop()
        self.indentLevel = self.indentLevel - 1

    def visitArray(self, ks):
        self.indentedPrint("[] of ")
        self.indentPush()
        ks.items.accept(self)
        self.indentPop()

    def visitScalar(self, ks):
        self.indentedPrint("{} ({}): {} Units: {} Example: {}".format(ks.title, ks.type, ks.description, ks.units, ks.example))


def main():
    parser = argparse.ArgumentParser("Generates C++ code from SignalK JSON specification")
    parser.add_argument("spec", help="vessel.json file")
    args = parser.parse_args()

    jsonSpec = JSONSchema().getSchema(args.spec)
    #print json.dumps(jsonSpec, sort_keys=True, indent=2)
    signalkSpec = KSchemaParser().parseSchema(jsonSpec)

    kpp = KPrettyPrinter()
    kpp.visit(signalkSpec)


if __name__ == '__main__':
    main()
