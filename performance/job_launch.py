import os
import shutil
import subprocess
import argparse

num_threads_per_node = {'mc' : 36, 'gpu' : 12}

new_env = os.environ.copy()

parser = argparse.ArgumentParser(description='Launch QE jobs.')
parser.add_argument('DIR', help='Directory with the test')
parser.add_argument('-i', '--input', help='Input file name', default='pw.in')
parser.add_argument('-p', '--partition', help='Target partition', choices=['mc', 'gpu'], default='mc')
parser.add_argument('-t', '--threads', type=int, help='Number of threads per rank', default=1)
parser.add_argument('-s', '--scratch', help='Scratch directory', default='/tmp')
parser.add_argument('-c', '--command', help='Execution command', default='pw.x')
parser.add_argument('-k', '--kpool', type=int, nargs='+', help='Number of k-point pools', default=[1])
parser.add_argument('-d', '--diag', type=int, nargs='+', help='Number of ranks for diagonalization', default=[1])
parser.add_argument('-R', '--run', action='store_true', help='Submit the jobs')
parser.add_argument('-T', '--time', help='max. execution time', default='0:30:00')
parser.add_argument('-S', '--suffix', help='additional suffix to the base directory name of the test', default='')
args = parser.parse_args()

def main():

    target_dir = args.scratch + '/' + os.path.basename(args.DIR) + args.suffix
    print("Terget directory: %s"%target_dir)

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    for k in args.kpool:

        for d in args.diag:
            num_ranks_diag = d
            num_ranks = d * k
            num_nodes = max((num_ranks * args.threads) / num_threads_per_node[args.partition], 1)
            label = "%iN_%iR_%iT"%(num_nodes, num_ranks, args.threads)

            target_subdir = target_dir + '/' + label
            if os.path.exists(target_subdir):
                shutil.rmtree(target_subdir)
            #if not os.path.exists(target_subdir):
            #    os.mkdir(target_subdir)

            shutil.copytree(args.DIR, target_subdir + '/')

            with open(target_subdir + '/run.slrm', 'w') as f:
                f.write('#!/bin/bash -l\n')
                f.write('#SBATCH --job-name="test_scf"\n')
                f.write('#SBATCH --nodes=%i\n'%num_nodes)
                f.write('#SBATCH --time=%s\n'%args.time)
                f.write('#SBATCH --output=slurm-stdout.txt\n')
                f.write('#SBATCH --error=slurm-stderr.txt\n')
                f.write('#SBATCH --account=csstaff\n')
                f.write('#SBATCH -C %s\n'%args.partition)
                f.write('MKL_NUM_THREADS=%i\n'%args.threads)
                f.write('OMP_NUM_THREADS=%i\n'%args.threads)
                f.write('srun -n %i --hint=nomultithread --unbuffered -c %i %s -i %s -npool %i -ndiag %i\n'%\
                    (num_ranks, args.threads, args.command, args.input, k, num_ranks_diag))

            if (args.run):
                print("Sumbinning the job: %s"%label)
                p = subprocess.Popen(["sbatch", "run.slrm"], cwd = target_subdir)
                p.wait()
    return


if __name__ == "__main__":
    main()
