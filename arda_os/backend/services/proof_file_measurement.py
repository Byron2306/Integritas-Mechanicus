"""Kernel fs-verity measurement tied to held file descriptors."""
from dataclasses import dataclass
import fcntl
import os
import stat
import struct

FS_IOC_MEASURE_VERITY = 0xc0046686


@dataclass
class MeasuredFile:
    path: str
    fd: int
    inode: int
    device: int
    algorithm: int
    digest: str

    def revalidate(self):
        if self.fd < 0:
            raise ValueError('measurement descriptor closed')
        st = os.stat(self.path, follow_symlinks=False)
        held = os.fstat(self.fd)
        if not stat.S_ISREG(st.st_mode) or (st.st_ino,st.st_dev) != (self.inode,self.device) or (held.st_ino,held.st_dev) != (self.inode,self.device):
            raise ValueError('measured file identity changed')
        algorithm,digest = measure_fd(self.fd)
        if (algorithm,digest) != (self.algorithm,self.digest):
            raise ValueError('kernel measurement changed')

    def entry(self):
        return {'path':self.path,'inode':self.inode,'device':self.device,
                'fs_verity_algorithm_id':self.algorithm,'fs_verity_digest':self.digest}

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def measure_fd(fd):
    buf = bytearray(struct.pack('=HH',0,64) + bytes(64))
    fcntl.ioctl(fd, FS_IOC_MEASURE_VERITY, buf, True)
    algorithm,size = struct.unpack('=HH',buf[:4])
    if (algorithm,size) not in ((1,32),(2,64)):
        raise ValueError('unsupported kernel fs-verity algorithm/digest size')
    return algorithm,bytes(buf[4:4+size]).hex()


def open_measured(path):
    if not os.path.isabs(path):
        raise ValueError('absolute measured path required')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError('regular file required')
        algorithm,digest=measure_fd(fd)
        result=MeasuredFile(path,fd,st.st_ino,st.st_dev,algorithm,digest)
        result.revalidate()
        return result
    except BaseException:
        os.close(fd)
        raise
