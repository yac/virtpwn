import provisioners.fabric
import exception

providers = {
    'fabric': provisioners.fabric.provision
}

def provision(pwn, prov_conf, tasks=None, user=None, provider='fabric'):
    try:
        pfun = providers[provider]
    except KeyError:
        raise exception.UnknownProvisioner(provider=provider)
    pfun(pwn, prov_conf, tasks=tasks, user=user)
