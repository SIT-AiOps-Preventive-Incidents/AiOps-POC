"""Let Kathara start labs on a host booted with ipv6.disable=1 (the capstone VM is).

Kathara asks Docker to set net.ipv6.* sysctls on every node, even with IPv6 off ("disable_ipv6=1"). With IPv6 disabled
in the kernel those files do not exist, and runc refuses to start the container. This drops the net.ipv6.* sysctls
only when /proc/sys/net/ipv6 is missing; on any other host Kathara behaves exactly as before.
Idempotent; touches only the Kathara copy inside NIKA's own virtualenv.   python patch_kathara_noipv6.py <DockerMachine.py>
"""
import sys

MARK = "# aiops-poc: no-ipv6 host patch"
path = sys.argv[1]
src = open(path).read()
if MARK in src:
    print("already patched")
    sys.exit(0)
a = "        sysctl_parameters = {**sysctl_parameters, **machine.meta['sysctls'], **sysctl_first_interface}\n"
b = "            sysctl_opts.update(iface_sysctls)\n"
assert a in src and b in src, "Kathara changed: patch points not found"
src = src.replace(a, a + f"""        if not __import__("os").path.exists("/proc/sys/net/ipv6"):  {MARK}
            sysctl_parameters = {{k: v for k, v in sysctl_parameters.items() if not k.startswith("net.ipv6.")}}
""", 1)
src = src.replace(b, b + f"""            if not __import__("os").path.exists("/proc/sys/net/ipv6"):  {MARK}
                sysctl_opts = {{o for o in sysctl_opts if not o.startswith("net.ipv6.")}}
""", 1)
open(path, "w").write(src)
print("patched", path)
