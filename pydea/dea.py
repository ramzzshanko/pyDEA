# The core DEA class, setting up and solving the linear programming problems using PuLP.


import numpy as np
import pandas as pd
import pulp


class DEA:
    """
    A container for the elements of a data envelopment analysis problem. Sets up the linear programmes and solves them with pulp.
    
    Requires:
    
        inputs: a pandas dataframe of the inputs to the DMUs
        outputs: a pandas dataframe of the outputs from the DMUs
        kind: 'VRS' or 'CRS'
    """

    
    def __init__(self, inputs, outputs, returns='CRS'):
        """
        Set up the DMUs' problems, ready to solve.
        """
        self.inputs = inputs
        self.outputs = outputs
        self.returns = returns
               
        self.J, self.I = self.inputs.shape  # no of firms, inputs
        self.R = self.outputs.shape[1]  # no of outputs
        self._i = np.arange(self.I)  # inputs
        self._r = np.arange(self.R)  # outputs
        self._j = np.arange(self.J)  # DMUs
        
        assert self.inputs.shape[0] == self.outputs.shape[0]  # check the inputs and outputs have the same number of DMUs
        
        self.dmus = self._create_problems()  # creates dictionary of pulp.LpProblem objects for the DMUs

        
    def _create_problems(self):
        """
        Iterate over the inputs and create a dictionary of LP problems, one for each DMU.
        """
        
        dmu_dict = {}
        for j0 in np.arange(self.inputs.shape[0]):
            dmu_dict[j0] = self._make_problem(j0)
        return dmu_dict
 
    
    def _make_problem(self, j0):
        """
        Create a pulp.LpProblem for a DMU.
        """
        
        ##Set up pulp
        prob = pulp.LpProblem("".join(["DMU_", str(j0)]), pulp.LpMaximize)
        self.inputWeights = pulp.LpVariable.dicts("inputWeight", (self._j, self._i), lowBound=0)
        self.outputWeights = pulp.LpVariable.dicts("outputWeight", (self._j, self._r), lowBound=0)
                
        ##Set returns to scale
        if self.returns == "CRS":
            w = 0
        elif self.returns == "VRS":
            w = pulp.LpVariable.dicts("w", (self._j, self._r))
        else:
            raise Exception(ValueError)

        ##Set up objective function
        prob += pulp.LpAffineExpression([(self.outputWeights[j0][r1], self.outputs.values[j0][r1]) for r1 in self._r]) - w

        ##Set up constraints
        prob += pulp.LpAffineExpression([(self.inputWeights[j0][i1], self.inputs.values[j0][i1]) for i1 in self._i]) == 1, "Norm_constraint"
        for j1 in self._j:
            prob += self._dmu_constraint(j0, j1)  - w <= 0, "".join(["DMU_constraint_", str(j1)])
        return prob
    
    
    def _dmu_constraint(self, j0, j1):
        """
        Calculate and return the DMU constraint for a single DMU's LP problem.
        """
        
        eOut = pulp.LpAffineExpression([(self.outputWeights[j0][r1], self.outputs.values[j1][r1]) for r1 in self._r])
        eIn = pulp.LpAffineExpression([(self.inputWeights[j0][i1], self.inputs.values[j1][i1]) for i1 in self._i])
        return eOut - eIn     

    
    def solve(self):
        """
        Iterate over the dictionary of DMUs' problems, solve them, and collate the results into a pandas dataframe.
        """
        
        sol_status = {}
        sol_results = {}
        sol_weights = {}
        sol_efficiency = {}
        for ind, problem in self.dmus.iteritems():
            problem.solve()
            sol_status[ind] = pulp.LpStatus[problem.status]
            sol_weights[ind] = {}
            for v in problem.variables():
                sol_weights[ind][v.name] = v.varValue
            sol_efficiency[ind] = pulp.value(problem.objective)
        self.results = pd.DataFrame.from_dict({'Status': sol_status, 'Efficiency': sol_efficiency, 'Weights': sol_weights})