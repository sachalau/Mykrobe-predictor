from .. import Variant
from .. import VariantSet

class Tree(dict):
    """Tree is defined by a dict of nodes"""
    def __init__(self):
        super(Tree, self).__init__()

class Node(object):
    """docstring for Node"""
    def __init__(self, children = []):
        super(Node, self).__init__()
        self.children = children ## List of nodes

    @property
    def samples(self):
        samples = []
        for child in self.children:
            samples.extend(child.samples)
        return samples ## List of sample below node in tree

    @property 
    def num_samples(self):
        return len(self.samples)

    @property
    def is_leaf(self):
        return False        

    @property
    def is_node(self):
        return True  

    @property
    def phylo_snps(self):
    	ingroup = VariantSet.objects(name__in = self.samples)
    	non_unique_variant_names = Variant.objects(variant_set__nin = ingroup ).distinct('name')
    	phylo_snps = Variant.objects(variant_set__in = ingroup, name__nin = non_unique_variant_names ).distinct('name')
        return phylo_snps
      

class Leaf(Node):

    def __init__(self, sample):
        super(Leaf, self).__init__()
        self.sample = sample 

    @property 
    def samples(self):
        return [self.sample]

    @property
    def is_leaf(self):
        return True

    @property
    def is_node(self):
        return False   


    
        
        