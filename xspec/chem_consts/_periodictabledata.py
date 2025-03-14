"""
dictionary of atomic numbers with element symbol as keys
"""
ptable = {
    'H': 1, 'He': 2, 'Li': 3, 'Be': 4, 'B': 5, 'C': 6, 'N': 7, 'O': 8,
    'F': 9, 'Ne': 10, 'Na': 11, 'Mg': 12, 'Al': 13, 'Si': 14, 'P': 15,
    'S': 16, 'Cl': 17, 'Ar': 18, 'K': 19, 'Ca': 20, 'Sc': 21, 'Ti': 22,
    'V': 23, 'Cr': 24, 'Mn': 25, 'Fe': 26, 'Co': 27, 'Ni': 28, 'Cu': 29,
    'Zn': 30, 'Ga': 31, 'Ge': 32, 'As': 33, 'Se': 34, 'Br': 35, 'Kr': 36,
    'Rb': 37, 'Sr': 38, 'Y': 39, 'Zr': 40, 'Nb': 41, 'Mo': 42, 'Tc': 43,
    'Ru': 44, 'Rh': 45, 'Pd': 46, 'Ag': 47, 'Cd': 48, 'In': 49, 'Sn': 50,
    'Sb': 51, 'Te': 52, 'I': 53, 'Xe': 54, 'Cs': 55, 'Ba': 56, 'La': 57,
    'Ce': 58, 'Pr': 59, 'Nd': 60, 'Pm': 61, 'Sm': 62, 'Eu': 63, 'Gd': 64,
    'Tb': 65, 'Dy': 66, 'Ho': 67, 'Er': 68, 'Tm': 69, 'Yb': 70, 'Lu': 71,
    'Hf': 72, 'Ta': 73, 'W': 74, 'Re': 75, 'Os': 76, 'Ir': 77, 'Pt': 78,
    'Au': 79, 'Hg': 80, 'Tl': 81, 'Pb': 82, 'Bi': 83, 'Po': 84, 'At': 85,
    'Rn': 86, 'Fr': 87, 'Ra': 88, 'Ac': 89, 'Th': 90, 'Pa': 91, 'U': 92,
    'Np': 93, 'Pu': 94, 'Am': 95, 'Cm': 96, 'Bk': 97, 'Cf': 98, 'Es': 99,
    'Fm': 100, 'Md': 101, 'No': 102, 'Lr': 103, 'Rf': 104, 'Db': 105,
    'Sg': 106, 'Bh': 107, 'Hs': 108, 'Mt': 109
}

"""
dictionary of atomic numbers with atomic number as keys
"""
ptableinverse = dict.fromkeys(ptable.values())
for k, v in ptable.items():
    ptableinverse[v] = k

"""
dictionary of atomic weights
"""
atom_weights = {'H': 1.00794,'He': 4.002602,'Li': 6.941,
                'Be': 9.012182,'B': 10.811,'C': 12.0107,
                'N': 14.0067,'O': 15.9994,'F': 18.9984032,
                'Ne': 20.1797,'Na': 22.98976928,'Mg': 24.305,
                'Al': 26.9815386,'Si': 28.0855,'P': 30.973762,
                'S': 32.065,'Cl': 35.453,'Ar': 39.948,
                'K': 39.0983,'Ca': 40.078,'Sc': 44.955912,
                'Ti': 47.867,'V': 50.9415,'Cr': 51.9961,
                'Mn': 54.938045,'Fe': 55.845,'Co': 58.933195,
                'Ni': 58.6934,'Cu': 63.546,'Zn': 65.38,
                'Ga': 69.723,'Ge': 72.64,'As': 74.9216,
                'Se': 78.96,'Br': 79.904,'Kr': 83.798,
                'Rb': 85.4678,'Sr': 87.62,'Y': 88.90585,
                'Zr': 91.224,'Nb': 92.90638,'Mo': 95.96,
                'Tc': 98.9062,'Ru': 101.07,'Rh': 102.9055,
                'Pd': 106.42,'Ag': 107.8682,'Cd': 112.411,
                'In': 114.818,'Sn': 118.71,'Sb': 121.76,
                'Te': 127.6,'I': 126.90447,'Xe': 131.293,
                'Cs': 132.9054519,'Ba': 137.327,'La': 138.90547,
                'Ce': 140.116,'Pr': 140.90765,'Nd': 144.242,
                'Pm': 145.0,'Sm': 150.36,'Eu': 151.964,
                'Gd': 157.25,'Tb': 158.92535,'Dy': 162.5,
                'Ho': 164.93032,'Er': 167.259,'Tm': 168.93421,
                'Yb': 173.054,'Lu': 174.9668,'Hf': 178.49,
                'Ta': 180.94788,'W': 183.84,'Re': 186.207,
                'Os': 190.23,'Ir': 192.217,'Pt': 195.084,
                'Au': 196.966569,'Hg': 200.59,'Tl': 204.3833,
                'Pb': 207.2,'Bi': 208.9804,'Po': 209.0,
                'At': 210.0,'Rn': 222.0,'Fr': 223.0,'Ra': 226.0,
                'Ac': 227.0,'Th': 232.0377,'Pa': 231.03588,
                'U': 238.02891,'Np': 237.0,'Pu': 244.0,
                'Am': 243.0,'Cm': 247.0,'Bk': 247.0,
                'Cf': 251.0, 'Air':1.0}

"""
densities of elements in g/cc
"""
density = {'H': 8.99e-05,'He': 0.0001785,'Li': 0.535,'Be': 1.848,
           'B': 2.46,'C': 2.26,'N': 0.001251,'O': 0.001429,
           'F': 0.001696,'Ne': 0.0009,'Na': 0.968,'Mg': 1.738,
           'Al': 2.7,'Si': 2.33,'P': 1.823,'S': 1.96,'Cl': 0.003214,
           'Ar': 0.001784,'K': 0.856,'Ca': 1.55,'Sc': 2.985,
           'Ti': 4.507,'V': 6.11,'Cr': 7.14,'Mn': 7.47,'Fe': 7.874,
           'Co': 8.9,'Ni': 8.908,'Cu': 8.92,'Zn': 7.14,'Ga': 5.904,
           'Ge': 5.323,'As': 5.727,'Se': 4.819,'Br': 3.12,'Kr': 0.00375,
           'Rb': 1.532,'Sr': 2.63,'Y': 4.472,'Zr': 6.511,
           'Nb': 8.57,'Mo': 10.28,'Tc': 11.5,'Ru': 12.37,
           'Rh': 12.45,'Pd': 12.023,'Ag': 10.49,'Cd': 8.65,
           'In': 7.31,'Sn': 7.31,'Sb': 6.697,'Te': 6.24,
           'I': 4.94,'Xe': 0.0059,'Cs': 1.879,'Ba': 3.51,
           'La': 6.146,'Ce': 6.689,'Pr': 6.64,'Nd': 7.01,
           'Pm': 7.264,'Sm': 7.353,'Eu': 5.244,'Gd': 7.901,
           'Tb': 8.219,'Dy': 8.551,'Ho': 8.795,'Er': 9.066,
           'Tm': 9.321,'Yb': 6.57,'Lu': 9.841,'Hf': 13.31,
           'Ta': 16.65,'W': 19.25,'Re': 21.02,'Os': 22.59,
           'Ir': 22.56,'Pt': 21.09,'Au': 19.3,'Hg': 13.534,
           'Tl': 11.85,'Pb': 11.34,'Bi': 9.78,'Po': 9.196,
           'At': None,'Rn': 0.00973,'Fr': None,'Ra': 5.0,
           'Ac': 10.07,'Th': 11.724,'Pa': 15.37,'U': 19.05,
           'Np': 20.45,'Pu': 19.816,'Am': 13.67,'Cm': 13.51,
           'Bk': 14.78,'Cf': 15.1, 'Air':1.225e-3}
