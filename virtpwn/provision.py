import provisioners.fabric
import exception

providers = {
    'fabric': provisioners.fabric.provision
}

def provision(pwn, tasks, provider='fabric'):
    try:
        pfun = providers[provider]
    except KeyError:
        raise exception.UnknownProvisioner(provider=provider)
    pfun(pwn, tasks)
