from bfabric import bfabric
from bfabric.src.paginator import read

b = bfabric.Bfabric()

responseLst = read(b, 'run', query={})

print(len(responseLst))