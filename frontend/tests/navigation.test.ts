/**
 * FE-22 — aba ativa da barra inferior (celular e tablet).
 *
 * Antes, a aba "Barbeiros" ficava ativa em "Dados da barbearia" porque a
 * regra comparava prefixo de texto: "/admin/barbershop" começa com
 * "/admin/barbers". Os testes cobrem todas as rotas autenticadas de
 * `App.tsx` nos três perfis, para a correção não quebrar outras abas.
 */
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import type { UserRole } from '../src/types'
import { activeTab, isSectionPath, TAB_ROUTES } from '../src/utils/navigation.ts'

describe('seção por segmento de caminho', () => {
  test('a própria seção e as subpáginas pertencem a ela', () => {
    assert.equal(isSectionPath('/admin/barbers', '/admin/barbers'), true)
    assert.equal(isSectionPath('/admin/barbers/12', '/admin/barbers'), true)
  })

  test('caminhos que só começam com o mesmo texto não pertencem (caso da auditoria)', () => {
    assert.equal(isSectionPath('/admin/barbershop', '/admin/barbers'), false)
    assert.equal(isSectionPath('/admin/barbersx', '/admin/barbers'), false)
    assert.equal(isSectionPath('/admin/servicesfoo', '/admin/services'), false)
  })
})

// Rota → aba que deve ficar ativa (null: a tela não tem aba na barra inferior)
const ESPERADO: Record<UserRole, [string, string, string | null][]> = {
  admin: [
    ['/admin', '', '/admin'],
    ['/admin/appointments', '', '/admin/appointments'],
    ['/admin/appointments', '?status=agendado', '/admin/appointments'],
    ['/admin/services', '', '/admin/services'],
    ['/admin/barbers', '', '/admin/barbers'],
    ['/admin/clients', '', '/admin/clients'],
    ['/admin/barbershop', '', null],
    ['/admin/barbershop/', '', null],
    ['/admin/barbers/', '', '/admin/barbers'],
    ['/account', '', null],
  ],
  barbeiro: [
    ['/barber/agenda', '', '/barber/agenda'],
    ['/barber/agenda', '?status=agendado', '/barber/agenda?status=agendado'],
    ['/account', '', '/account'],
  ],
  cliente: [
    ['/', '', '/'],
    ['/appointments/new', '', '/appointments/new'],
    ['/appointments/new', '?reschedule=12', '/appointments/new'],
    ['/appointments', '', '/appointments'],
    ['/services', '', '/services'],
    ['/barbers', '', '/barbers'],
    ['/account', '', null],
  ],
}

for (const role of Object.keys(ESPERADO) as UserRole[]) {
  describe(`perfil ${role}`, () => {
    for (const [pathname, search, esperado] of ESPERADO[role]) {
      test(`${pathname}${search} → ${esperado ?? 'nenhuma aba'}`, () => {
        assert.equal(activeTab(role, pathname, search), esperado)
        const ativas = TAB_ROUTES[role].filter((tab) => tab.isActive(pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname, search))
        assert.ok(ativas.length <= 1, `mais de uma aba ativa: ${ativas.map((tab) => tab.label).join(', ')}`)
      })
    }

    test('cada aba fica ativa na própria tela', () => {
      for (const tab of TAB_ROUTES[role]) {
        const [pathname, query = ''] = tab.to.split('?')
        assert.equal(activeTab(role, pathname, query ? `?${query}` : ''), tab.to, tab.label)
      }
    })
  })
}

test('"Barbeiros" não fica ativa em "Dados da barbearia" (FE-22)', () => {
  assert.notEqual(activeTab('admin', '/admin/barbershop'), '/admin/barbers')
})
