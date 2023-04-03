"""
Unit tests for the different datasets of goli/features/featurizer.py
"""

import numpy as np
import unittest as ut
from copy import deepcopy
from rdkit import Chem
import datamol as dm
import torch

from goli.features.featurizer import GraphDict
from goli.features.positional_encoding import graph_positional_encoder
from goli.nn.encoders import laplace_pos_encoder, mlp_encoder, signnet_pos_encoder

# TODO: Test the MLP_encoder and signnet_pos_encoder


class test_positional_encoder(ut.TestCase):
    smiles = [
        "C",
        "CC",
        "CC.CCCC",
        "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "OCCc1c(C)[n+](cs1)Cc2cnc(C)nc2N",
        "O1C=C[C@H]([C@H]1O2)c3c2cc(OC)c4c3OC(=O)C5=C4CCC(=O)5",
    ]
    mols = [dm.to_mol(s) for s in smiles]
    adjs = [Chem.rdmolops.GetAdjacencyMatrix(mol) for mol in mols]

    def test_laplacian_eigvec(self):
        for ii, adj in enumerate(deepcopy(self.adjs)):
            for num_pos in [1, 2, 4]:  # Can't test too much eigs because of multiplicities
                for disconnected_comp in [True, False]:
                    err_msg = f"adj_id={ii}, num_pos={num_pos}, disconnected_comp={disconnected_comp}"

                    # returns a dictionary of computed pe
                    pos_encoding_as_features = {
                        "pos_type": "laplacian_eigvec",
                        "num_pos": num_pos,
                        "disconnected_comp": disconnected_comp,
                    }
                    num_nodes = adj.shape[0]
                    pe_dict = graph_positional_encoder(adj, num_nodes, pos_encoding_as_features)
                    pos_enc_sign_flip = pe_dict["eigvecs"]
                    pos_enc_no_flip = pe_dict["eigvals"]

                    self.assertEqual(list(pos_enc_sign_flip.shape), [adj.shape[0], num_pos], msg=err_msg)
                    self.assertIsNone(pos_enc_no_flip)

                    # Compute eigvals and eigvecs
                    lap = np.diag(np.sum(adj, axis=1)) - adj
                    eigvals, eigvecs = np.linalg.eig(lap)
                    sort_idx = np.argsort(eigvals)
                    eigvals, eigvecs = eigvals[sort_idx], eigvecs[:, sort_idx]
                    eigvecs = eigvecs / (np.sum(eigvecs**2, axis=0, keepdims=True) + 1e-8)

                    true_num_pos = min(num_pos, len(eigvals))
                    eigvals, eigvecs = eigvals[:true_num_pos], eigvecs[:, :true_num_pos]
                    eigvecs = np.sign(eigvecs[0:1, :]) * eigvecs
                    pos_enc_sign_flip = np.sign(pos_enc_sign_flip[0:1, :]) * pos_enc_sign_flip

                    # Compare the positional encoding
                    if disconnected_comp and ("." in self.smiles[ii]):
                        self.assertGreater(np.max(np.abs(eigvecs - pos_enc_sign_flip)), 1e-3)
                    elif not ("." in self.smiles[ii]):
                        np.testing.assert_array_almost_equal(
                            eigvecs, pos_enc_sign_flip[:, :true_num_pos], decimal=6, err_msg=err_msg
                        )

    def test_laplacian_eigvec_eigval(self):
        for ii, adj in enumerate(deepcopy(self.adjs)):
            for num_pos in [1, 2, 4]:  # Can't test too much eigs because of multiplicities
                for disconnected_comp in [True, False]:
                    err_msg = f"adj_id={ii}, num_pos={num_pos}, disconnected_comp={disconnected_comp}"

                    # returns a dictionary of computed pe
                    pos_encoding_as_features = {
                        "pos_type": "laplacian_eigvec_eigval",
                        "num_pos": num_pos,
                        "disconnected_comp": disconnected_comp,
                    }
                    num_nodes = adj.shape[0]
                    pe_dict = graph_positional_encoder(adj, num_nodes, pos_encoding_as_features)
                    pos_enc_sign_flip = pe_dict["eigvecs"]
                    pos_enc_no_flip = pe_dict["eigvals"]

                    self.assertEqual(list(pos_enc_sign_flip.shape), [adj.shape[0], num_pos], msg=err_msg)
                    self.assertEqual(list(pos_enc_no_flip.shape), [adj.shape[0], num_pos], msg=err_msg)

                    # Compute eigvals and eigvecs
                    lap = np.diag(np.sum(adj, axis=1)) - adj
                    eigvals, eigvecs = np.linalg.eig(lap)
                    sort_idx = np.argsort(eigvals)
                    eigvals, eigvecs = eigvals[sort_idx], eigvecs[:, sort_idx]
                    eigvecs = eigvecs / (np.sum(eigvecs**2, axis=0, keepdims=True) + 1e-8)

                    true_num_pos = min(num_pos, len(eigvals))
                    eigvals, eigvecs = eigvals[:true_num_pos], eigvecs[:, :true_num_pos]
                    eigvecs = np.sign(eigvecs[0:1, :]) * eigvecs
                    pos_enc_sign_flip = np.sign(pos_enc_sign_flip[0:1, :]) * pos_enc_sign_flip

                    if not ("." in self.smiles[ii]):
                        np.testing.assert_array_almost_equal(
                            eigvecs, pos_enc_sign_flip[:, :true_num_pos], decimal=6, err_msg=err_msg
                        )
                        np.testing.assert_array_almost_equal(
                            eigvals, pos_enc_no_flip[0, :true_num_pos], decimal=6, err_msg=err_msg
                        )

    # didn't actually check the exact computation result because the code was adapted
    def test_rwse(self):
        for ii, adj in enumerate(deepcopy(self.adjs)):
            for ksteps in [1, 2, 4]:
                err_msg = f"adj_id={ii}, ksteps={ksteps}"

                num_nodes = adj.shape[0]
                pos_encoding_as_features = {"pos_type": "rwse", "ksteps": ksteps}
                pe_dict = graph_positional_encoder(adj, num_nodes, pos_encoding_as_features)
                rwse_embed = pe_dict["rwse"]
                self.assertEqual(list(rwse_embed.shape), [num_nodes, ksteps], msg=err_msg)

    # TODO: work in progress

    """
    continue debugging here, see how to adapt the laplace_pos_encoder
    code running now, question is where to add the laplace_pos_encoder
    """

    def test_laplacian_eigvec_with_encoder(self):
        for ii, adj in enumerate(deepcopy(self.adjs)):
            for num_pos in [2, 4, 8]:  # Can't test too much eigs because of multiplicities
                for disconnected_comp in [True, False]:
                    for model_type in ["Transformer", "DeepSet", "MLP"]:
                        err_msg = f"adj_id={ii}, num_pos={num_pos}, disconnected_comp={disconnected_comp}"

                        # returns a dictionary of computed pe
                        pos_encoding_as_features = {
                            "pos_type": "laplacian_eigvec_eigval",
                            "num_pos": num_pos,
                            "disconnected_comp": disconnected_comp,
                        }
                        num_nodes = adj.shape[0]
                        pe_dict = graph_positional_encoder(adj, num_nodes, pos_encoding_as_features)

                        input_keys = ["eigvecs", "eigvals"]
                        in_dim = num_pos
                        hidden_dim = 64
                        out_dim = 64
                        num_layers = 1

                        pos_enc_sign_flip = torch.from_numpy(pe_dict["eigvecs"])

                        pos_enc_no_flip = torch.from_numpy(pe_dict["eigvals"])

                        eigvecs = pos_enc_sign_flip
                        eigvals = pos_enc_no_flip
                        g = GraphDict(
                            {
                                "adj": torch.as_tensor(adj).to_sparse_coo(),
                                "ndata": {"eigvals": eigvals, "eigvecs": eigvecs},
                                "edata": {},
                            }
                        )
                        batch = g.make_pyg_graph()

                        encoder = laplace_pos_encoder.LapPENodeEncoder(
                            input_keys=input_keys,
                            output_keys=["node"],
                            in_dim=in_dim,  # Size of Laplace PE embedding
                            hidden_dim=hidden_dim,
                            out_dim=out_dim,
                            model_type=model_type,  # 'Transformer' or 'DeepSet'
                            num_layers=num_layers,
                            num_layers_post=2,  # Num. layers to apply after pooling
                            dropout=0.1,
                            first_normalization=None,
                        )

                        hidden_embed = encoder(batch, key_prefix=None)
                        assert "node" in hidden_embed.keys()
                        self.assertEqual(list(hidden_embed["node"].shape), [num_nodes, out_dim], msg=err_msg)


if __name__ == "__main__":
    ut.main()
