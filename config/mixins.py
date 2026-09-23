class TenantScopedQuerysetMixin:
    """
    Filtra querysets para mostrar apenas dados da barbearia do usuário logado.
    """
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Superusuário é operador da plataforma, não pertence a um
            # tenant. A exceção é explícita e não pode ser inferida de um
            # barbershop_id nulo.
            if user.is_superuser:
                return super().get_queryset()
            if user.tipo_perfil == 'barbeiro':
                # Um papel de barbeiro sem perfil profissional é um estado
                # inconsistente. Além de não poder causar 500, ele não pode
                # herdar a visão de todo o tenant.
                barbeiro = getattr(user, 'perfil_barbeiro', None)
                if barbeiro is not None:
                    return super().get_queryset().filter(
                        barbershop=barbeiro.barbershop
                    )
                return super().get_queryset().none()
            if user.barbershop_id:
                # Cobre admin e cliente: ambos têm `barbershop` preenchido
                # e devem ver os dados da própria barbearia (cliente
                # precisa ver serviços/barbeiros para poder agendar).
                return super().get_queryset().filter(barbershop_id=user.barbershop_id)
        return super().get_queryset().none()
