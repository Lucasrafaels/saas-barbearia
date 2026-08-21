from django.core.exceptions import PermissionDenied

class TenantScopedQuerysetMixin:
    """
    Filtra querysets para mostrar apenas dados da barbearia do usuário logado.
    """
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.tipo_perfil == 'barbeiro':
                # related_name real do OneToOne em Barber é 'perfil_barbeiro'
                # (era 'barber_profile', que não existe no model).
                return super().get_queryset().filter(
                    barbershop=user.perfil_barbeiro.barbershop
                )
            if user.barbershop_id:
                # Cobre admin e cliente: ambos têm `barbershop` preenchido
                # e devem ver os dados da própria barbearia (cliente
                # precisa ver serviços/barbeiros para poder agendar).
                return super().get_queryset().filter(barbershop_id=user.barbershop_id)
        return super().get_queryset().none()
