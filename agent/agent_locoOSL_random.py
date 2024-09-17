import os
import pickle
import time

import copy
import numpy as np

import evaluation_pb2
import evaluation_pb2_grpc
import grpc
import gymnasium as gym

from utils import LocoRemoteConnection

"""
Define your custom observation keys here
"""
custom_obs_keys = [
    'terrain',        
    'internal_qpos',
    'internal_qvel',
    'grf',
    'torso_angle',
    'socket_force',
    'torso_angle',
    'model_root_pos',
    'model_root_vel',
    'muscle_length',
    'muscle_velocity',
    'muscle_force',
    'act',
    'act_dot',
]

def pack_for_grpc(entity):
    return pickle.dumps(entity)

def unpack_for_grpc(entity):
    return pickle.loads(entity)

class Policy:

    def __init__(self, env):
        self.action_space = env.action_space

    def __call__(self, env):
        return self.action_space.sample()

def get_custom_observation(rc, obs_keys):
    """
    Use this function to create an observation vector from the 
    environment provided observation dict for your own policy.
    By using the same keys as in your local training, you can ensure that 
    your observation still works.
    """

    obs_dict = rc.get_obsdict()
    # add new features here that can be computed from obs_dict
    # obs_dict['qpos_without_xy'] = np.array(obs_dict['internal_qpos'][2:35].copy())

    return rc.obsdict2obsvec(obs_dict, obs_keys)

def generateDict():
    """
    Example function to generate the dictionary for the
    """
    BODY_WEIGHT = 78.6689 * 9.81 # Total body mass (incl. OSL leg) * gravity

    temp_dict = {}
    temp_dict['e_stance'] = {}
    temp_dict['e_stance']['gain'] = {}
    temp_dict['e_stance']['threshold'] = {}
    temp_dict['e_stance']['gain']['knee_stiffness'] = 99.372
    temp_dict['e_stance']['gain']['knee_damping'] = 3.180
    temp_dict['e_stance']['gain']['knee_target_angle'] = np.deg2rad(5)
    temp_dict['e_stance']['gain']['ankle_stiffness'] = 19.874
    temp_dict['e_stance']['gain']['ankle_damping'] = 0
    temp_dict['e_stance']['gain']['ankle_target_angle'] = np.deg2rad(-2)
    temp_dict['e_stance']['threshold']['load'] = (0.25 * BODY_WEIGHT, 'above')
    temp_dict['e_stance']['threshold']['ankle_angle'] = (np.deg2rad(6), 'above')

    temp_dict['l_stance'] = {}
    temp_dict['l_stance']['gain'] = {}
    temp_dict['l_stance']['threshold'] = {}
    temp_dict['l_stance']['gain']['knee_stiffness'] = 99.372
    temp_dict['l_stance']['gain']['knee_damping'] = 1.272
    temp_dict['l_stance']['gain']['knee_target_angle'] = np.deg2rad(8)
    temp_dict['l_stance']['gain']['ankle_stiffness'] = 79.498
    temp_dict['l_stance']['gain']['ankle_damping'] = 0.063
    temp_dict['l_stance']['gain']['ankle_target_angle'] = np.deg2rad(-20)
    temp_dict['l_stance']['threshold']['load'] = (0.15 * BODY_WEIGHT, 'below')

    temp_dict['e_swing'] = {}
    temp_dict['e_swing']['gain'] = {}
    temp_dict['e_swing']['threshold'] = {}
    temp_dict['e_swing']['gain']['knee_stiffness'] = 39.749
    temp_dict['e_swing']['gain']['knee_damping'] = 0.063
    temp_dict['e_swing']['gain']['knee_target_angle'] = np.deg2rad(60)
    temp_dict['e_swing']['gain']['ankle_stiffness'] = 7.949
    temp_dict['e_swing']['gain']['ankle_damping'] = 0
    temp_dict['e_swing']['gain']['ankle_target_angle'] = np.deg2rad(25)
    temp_dict['e_swing']['threshold']['knee_angle'] = (np.deg2rad(50), 'above')
    temp_dict['e_swing']['threshold']['knee_vel'] = (np.deg2rad(3), 'below')

    temp_dict['l_swing'] = {}
    temp_dict['l_swing']['gain'] = {}
    temp_dict['l_swing']['threshold'] = {}
    temp_dict['l_swing']['gain']['knee_stiffness'] = 15.899
    temp_dict['l_swing']['gain']['knee_damping'] = 3.816
    temp_dict['l_swing']['gain']['knee_target_angle'] = np.deg2rad(5)
    temp_dict['l_swing']['gain']['ankle_stiffness'] = 7.949
    temp_dict['l_swing']['gain']['ankle_damping'] = 0
    temp_dict['l_swing']['gain']['ankle_target_angle'] = np.deg2rad(15)
    temp_dict['l_swing']['threshold']['load'] = (0.4 * BODY_WEIGHT, 'above')
    temp_dict['l_swing']['threshold']['knee_angle'] = (np.deg2rad(30), 'below')

    OSL_PARAM_LIST = {}
    for idx in np.arange(4):
        OSL_PARAM_LIST[idx] = {}
        OSL_PARAM_LIST[idx] = copy.deepcopy(temp_dict)

    return OSL_PARAM_LIST


time.sleep(60)

LOCAL_EVALUATION = os.environ.get("LOCAL_EVALUATION")

if LOCAL_EVALUATION:
    rc = LocoRemoteConnection("environment:8086")
else:
    rc = LocoRemoteConnection("localhost:8086")

# if LOCAL_EVALUATION:
#     channel = grpc.insecure_channel("environment:8086")
# else:
#     channel = grpc.insecure_channel("localhost:8086")

# stub = evaluation_pb2_grpc.EnvironmentStub(channel)
# env_shell = EnvShell(stub)
policy = Policy(rc)

osl_dict = generateDict() # Small test for agent

# compute correct observation space using the custom keys
shape = get_custom_observation(rc, custom_obs_keys).shape
rc.set_output_keys(custom_obs_keys)

flat_completed = None
trial = 0
while not flat_completed:
    flag_trial = None # this flag will detect the end of an episode/trial
    ret = 0

    print(f"LOCO-OSL: Start Resetting the environment and get 1st obs of iter {trial}")
    
    obs = rc.reset(osl_dict)

    # obs = unpack_for_grpc(
    #     stub.reset(
    #         evaluation_pb2.Package(SerializedEntity=pack_for_grpc(osl_dict))
    #     ).SerializedEntity
    # )

    """
    Example of changing the OSL parameter set for the episode
    """
    if trial == 0:
        mode = np.array([0])
    else:
        mode = np.array([1])

    rc.change_osl_mode(mode)

    # stub.change_osl_mode(
    #     evaluation_pb2.Package(SerializedEntity=pack_for_grpc(mode))
    # ).SerializedEntity


    print(f"Trial: {trial}, flat_completed: {flat_completed}")
    counter = 0
    while not flag_trial:

        ################################################
        ## Replace with your trained policy.
        action = rc.action_space.sample()
        ################################################

        base = rc.act_on_environment(action)

        obs = base["feedback"][0]
        flag_trial = base["feedback"][2]
        flat_completed = base["eval_completed"]
        ret += base["feedback"][1]

        if flag_trial:
            print(f"Return was {ret}")
            print("*" * 100)
            break
        counter += 1
    trial += 1