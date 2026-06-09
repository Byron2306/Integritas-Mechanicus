#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct arda_identity {
    __u64 inode;
    __u32 dev;
    __u32 pad;
} __attribute__((packed));

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, struct arda_identity);
    __type(value, __u32);
} arda_harmony SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} arda_state SEC(".maps");

SEC("lsm/bprm_check_security")
int BPF_PROG(arda_sovereign_ignition, struct linux_binprm *bprm, int ret)
{
    if (ret != 0) return ret;
    if (!bprm->file) return 0;

    struct arda_identity key = {0};
    key.inode = bprm->file->f_inode->i_ino;
    key.dev = bprm->file->f_inode->i_sb->s_dev;
    key.pad = 0;

    // Forensic Debug: Log raw hex of first 8 bytes of the key (inode)
    unsigned char *k = (unsigned char *)&key;
    bpf_printk("ARDA_LSM: lookup ino=%llu, dev=%u", key.inode, key.dev);
    bpf_printk("ARDA_LSM: key_hex: %02x %02x %02x %02x %02x %02x %02x %02x",
               k[0], k[1], k[2], k[3], k[4], k[5], k[6], k[7]);
    bpf_printk("ARDA_LSM: key_hex: %02x %02x %02x %02x %02x %02x %02x %02x",
               k[8], k[9], k[10], k[11], k[12], k[13], k[14], k[15]);

    __u32 *is_harmonic = bpf_map_lookup_elem(&arda_harmony, &key);
    
    // Check Sovereignty State (0 = Audit/Permissive, 1 = Enforcement)
    __u32 state_idx = 0;
    __u32 *state = bpf_map_lookup_elem(&arda_state, &state_idx);
    __u32 enforcement = (state && *state == 1);

    if (!is_harmonic || *is_harmonic == 0) {
        if (enforcement) {
            bpf_printk("ARDA_LSM: [ENFORCE] DENIED execution for inode %llu", key.inode);
            return -1; // -EPERM
        } else {
            bpf_printk("ARDA_LSM: [AUDIT] would deny execution for inode %llu", key.inode);
            return 0; // Allow in audit mode
        }
    }

    bpf_printk("ARDA_LSM: [PASS] ALLOWED execution for inode %llu", key.inode);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
