#!flask/bin/python

""" 
This scripts runs on localhost by executing:
$ python flax.py

it provides a REST TO WSDL wrapper

the INPUT is a workunit ID given as URL:
http://localhost:5000/bfabric/api/workunitid/142914

the OUTPUT is a list of the relative path resource.
{
  "resources": [
    "p1000/Proteomics/RData/cpanse_20160701/F231466.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F231465.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F231464.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F231462.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230472.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230471.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230470.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230469.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230468.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230467.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230466.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230465.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230284.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230283.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230281.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230280.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230236.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230234.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230232.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230230.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230228.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230226.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230223.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230221.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230220.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230217.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230209.RData", 
    "p1000/Proteomics/RData/cpanse_20160701/F230201.RData"
  ]
}


this script can be used as a bfabric <-> shiny wrapper

Christian Panse <cp@fgcz.ethz.ch
Witold E. Wolski <wew@fgcz.ethz.ch>
2016-07-05 1700

"""

from flask import Flask, jsonify
from bfabric import bfabric

app = Flask(__name__)

def wu2rrp(wuid):
    bfapp = bfabric.Bfabric(login='pfeeder')
    workunit = bfapp.read_object(endpoint='resource', obj={'workunitid': wuid})

    res = []
    for i in workunit:
        res.append(i.relativepath)
    return res

@app.route('/bfabric/api/workunitid/<int:wu_id>', methods=['GET'])
def get_workunitid(wu_id):
    res = wu2rrp(wu_id)

    if len(res) == 0:
        return jsonify({'error': 'no resources found.'})
        # abort(404)

    return jsonify({'resources': res})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
