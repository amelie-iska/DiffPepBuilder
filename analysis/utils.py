import numpy as np
import os
import re
import io
from data import protein, residue_constants
from scipy.spatial.transform import Rotation
from openfold.utils import rigid_utils


CA_IDX = residue_constants.atom_order['CA']
Rigid = rigid_utils.Rigid

def write_from_string(string:io.StringIO, file):
    f = open(file, 'w')
    f.write(string)

def create_full_prot(
        atom37: np.ndarray,
        atom37_mask: np.ndarray,
        aatype=None,
        residue_index=None,
        chain_index=None,
        b_factors=None,
    ):
    assert atom37.ndim == 3
    assert atom37.shape[-1] == 3
    assert atom37.shape[-2] == 37
    n = atom37.shape[0]
    if residue_index is None:
        residue_index = np.arange(n)
    if chain_index is None:
        chain_index = np.zeros(n)
    if b_factors is None:
        b_factors = np.zeros([n, 37])
    if aatype is None:
        aatype = np.zeros(n, dtype=int)
    return protein.Protein(
        atom_positions=atom37,
        atom_mask=atom37_mask,
        aatype=aatype,
        residue_index=residue_index,
        chain_index=chain_index,
        b_factors=b_factors)


def write_prot_to_pdb(
        prot_pos: np.ndarray,
        file_path: str,
        coordinate_bias: np.ndarray=None,  # [N_res, 3]
        aatype: np.ndarray=None,
        residue_index: np.ndarray=None,
        chain_index: np.ndarray=None,
        overwrite=False,
        no_indexing=True,
        b_factors=None,
    ):
    if overwrite:
        max_existing_idx = 0
    else:
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_name = os.path.basename(file_path).strip('.pdb')
        existing_files = [x for x in os.listdir(file_dir) if file_name in x]
        max_existing_idx = max([
            int(re.findall(r'_(\d+).pdb', x)[0]) for x in existing_files if re.findall(r'_(\d+).pdb', x)
            if re.findall(r'_(\d+).pdb', x)] + [0])
    if not no_indexing:
        save_path = file_path.replace('.pdb', '') + f'_{max_existing_idx+1}.pdb'
    else:
        save_path = file_path
    with open(save_path, 'w') as f:
        if prot_pos.ndim == 4:  # [T, N_res, 37, 3]
            for t, pos37 in enumerate(prot_pos):
                atom37_mask = np.sum(np.abs(pos37), axis=-1) > 1e-7
                if coordinate_bias is not None:
                    pos37 = pos37 + coordinate_bias[:, None, :]
                prot = create_full_prot(
                    pos37, atom37_mask, aatype=aatype, residue_index=residue_index, chain_index=chain_index, b_factors=b_factors)
                pdb_prot = protein.to_pdb(prot, model=t+1, add_end=False)
                f.write(pdb_prot)
        elif prot_pos.ndim == 3:  # [N_res, 37, 3]
            atom37_mask = np.sum(np.abs(prot_pos), axis=-1) > 1e-7
            if coordinate_bias is not None:
                prot_pos = prot_pos + coordinate_bias[:, None, :]
            prot = create_full_prot(
                prot_pos, atom37_mask, aatype=aatype, residue_index=residue_index, chain_index=chain_index, b_factors=b_factors)
            pdb_prot = protein.to_pdb(prot, model=1, add_end=False)
            f.write(pdb_prot)
        else:
            raise ValueError(f'Invalid positions shape {prot_pos.shape}')
        f.write('END')
    return save_path


def rigids_to_se3_vec(frame, scale_factor=1.0):
    trans = frame[:, 4:] * scale_factor
    rotvec = Rotation.from_quat(frame[:, :4]).as_rotvec()
    se3_vec = np.concatenate([rotvec, trans], axis=-1)
    return se3_vec
