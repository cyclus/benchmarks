#! /usr/bin/env python

# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from pprint import pprint, pformat
try:
    import simplejson as json
except ImportError:
    import json
from lxml import etree
from pyne import nucname


class CyclusTransformer(object):
    """I'm a little teapot."""
    
    def __init__(self, jfile,rfile):
        with open(jfile, 'r') as f:
            self.jroot = json.load(f)
        self.xroot = etree.Element('simulation')
        self.rroot = etree.parse(rfile).getroot()
            
    def __str__(self):
        s = "\n".join(["JSON Root =", '-'*40, pformat(self.jroot), '', ''])
        s += "\n".join(["XML Root =", '-'*40, etree.tostring(self.xroot, pretty_print=True)])
        return s
    
    def visit(self, node=None):
        if node is None:
            node = self.jroot
        for key, value in node.iteritems():
            methname = 'visit_' + key
            if hasattr(self, methname):
                meth = getattr(self, methname)
                meth(value)
                
    def visit_materials(self, node):
        for name, value in node.iteritems():
            self.visit_material(name, value)
            
    def visit_material(self, name, mat):
        # Add commoditiy information
        commodity = etree.SubElement(self.xroot, 'commodity')
        commodname = etree.SubElement(commodity, 'name')
        commodname.text = name
        
        # Add recipe
        recipe = etree.SubElement(self.xroot, 'recipe')
        recipename = etree.SubElement(recipe, 'name')
        recipename.text = name + '_recipe'
        basis = etree.SubElement(recipe, 'basis')
        basis.text = 'mass'
        if mat['recipe']:
            self.visit_recipe_material(mat,recipe)
        else:
            self.visit_stored_recipe(name,recipe)

    def visit_recipe_material(self,mat,recipe):
        constraints = mat['constraints']
        for constraint in constraints:
            if nucname.isnuclide(constraint[0]):
                self.visit_nuclide(recipe,
                                   nucname.zzaaam(constraint[0]),
                                   constraint[1])

    def visit_stored_recipe(self,name,recipe):
        nodes = self.iso_nodes(name)
        for node in nodes:
            self.visit_nuclide(recipe,node[0].text,node[1].text)

    def visit_nuclide(self,recipe,nuc,val):
        isotope = etree.SubElement(recipe,'isotope')
        isoid = etree.SubElement(isotope,'id')
        isoid.text=str(nuc)
        isoval = etree.SubElement(isotope,'comp')
        isoval.text=str(val)

    def iso_nodes(self,name):
        recipe_names = self.rroot.xpath('recipe/name')
        for i in range(len(recipe_names)):
            if recipe_names[i].text == name:
                return self.rroot.xpath('recipe')[i].findall('isotope')
        raise RecipeError("No recipe named " + name 
                          + " found in " + self.rfile)

class RecipeError(Exception):
    """Exception indicating a Recipe wasn't found."""
    pass


# <codecell>

ct = CyclusTransformer('nea1a.json','nea_recipes.xml')
ct.visit()
print ct

# <codecell>


