import gym
from gym.spaces import MultiDiscrete, Box
import numpy as np
from collections import namedtuple as tup
import os
from subprocess import run
from time import time
class ChipyardFIRRTLEnv(gym.Env):

    def build_chipyard(self, action):
        targetDir = self.config.targetDir + '/current'
        top = f'{self.config.package}.{self.config.top}'
        config = f'{self.config.package}:{self.config.config}'

        os.makedirs(targetDir + '/include', exist_ok=True)

        buid_env = os.environ.copy()
        for par, val in zip(self.parameters, list(action)):
            buid_env[par.name] = f'{val}'
        buid_env['gemmini_header'] = ('/..' * (len(self.config.chipyardDir.split('/')) + 4)) + targetDir + '/include/gemmini_params.h'
        buid_env['has_training_convs'] = '0'

        init_time = time()
        #build_process = run(f"""{self.config.sbt}  ";project fpga_platforms; runMain chipyard.Generator  --target-dir { targetDir } --name {self.config.prefix} --top-module {top} --legacy-configs {config}" """,
        #                    shell = True, capture_output=True, text=True, cwd = self.config.chipyardDir, env = buid_env)
        build_process = run(f"""java -cp {self.config.chipyardDir}/fpga/target/scala-2.12/fpga_platforms-assembly-1.6.jar chipyard.Generator  --target-dir { targetDir } --name {self.config.prefix} --top-module {top} --legacy-configs {config}""",
                            shell = True, capture_output=True, text=True, cwd = self.config.chipyardDir, env = buid_env)

        elapsed_time = time() - init_time
        print('Finished FIRRTL ...')
        print(f'Time elapsed: {elapsed_time}')

        with open(f'{targetDir}/{self.config.prefix}.firrtl.stdout.log', 'w') as f:
            f.write(build_process.stdout)
            f.close()

        with open(f'{targetDir}/{self.config.prefix}.firrtl.stderr.log', 'w') as f:
            f.write(build_process.stderr)
            f.close()

        failed = '[error]' in build_process.stdout

        return failed, elapsed_time

    def __init__(self, config):

        super(ChipyardFIRRTLEnv, self).__init__()
        # Define action and observation space
        Parameter = tup('Parameter', 'name dim')

        self.parameters = [Parameter('meshRC', 3),
        Parameter('sp_factor', 9),
        Parameter('acc_factor', 9),
        Parameter('has_training_convs', 2),
        Parameter('has_max_pool', 2),
        Parameter('has_nonlinear_activations', 2)]

        self.action_space = MultiDiscrete(np.array([par.dim for par in self.parameters]))
        self.observation_space = Box(low=0, high=1.0, shape=(1,), dtype=np.float64)

        self.config = config


    def step(self, action):
        print(action)
        done, elapsed_time = self.build_chipyard(action)
        observation = np.array([0.5])
        reward  = 0
        info = {"elapsed_time", elapsed_time}

        return observation, reward, done, info

    def reset(self):
        done, elapsed_time = self.build_chipyard([])
        print(done)
        observation = np.array([elapsed_time])
        return observation