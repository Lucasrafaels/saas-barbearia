/**
 * FE-14 — status da barbearia na barra lateral e no início do cliente.
 *
 * O status usa só dados que já existem: `ativo`, `dias_funcionamento` e o
 * horário de abertura e fechamento. Nunca pode contradizer o calendário de
 * agendamento, que usa `isOpenOn` com a mesma configuração.
 */
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { addDays, isoWeekday } from '../src/utils/format.ts'
import { isOpenOn, shopHoursStatus, WEEKDAYS } from '../src/utils/shop.ts'

const SEXTA = '2026-11-13'
const SABADO = '2026-11-14'
const TODOS_OS_DIAS = [1, 2, 3, 4, 5, 6, 7]
const h = (hora: number, minuto = 0) => hora * 60 + minuto

function barbearia(extra: Partial<{ dias_funcionamento: number[]; ativo: boolean; horario_abertura: string; horario_fechamento: string }> = {}) {
  return { horario_abertura: '09:00:00', horario_fechamento: '19:00:00', dias_funcionamento: TODOS_OS_DIAS, ativo: true, ...extra }
}

describe('dia da semana ISO', () => {
  test('segue o padrão da API (1 = segunda … 7 = domingo)', () => {
    assert.equal(isoWeekday('2026-11-16'), 1)
    assert.equal(isoWeekday(SEXTA), 5)
    assert.equal(isoWeekday(SABADO), 6)
    assert.equal(isoWeekday('2026-11-15'), 7)
  })
})

describe('barbearia aberta hoje', () => {
  test('dentro do horário: aberta até o fechamento', () => {
    assert.deepEqual(shopHoursStatus(barbearia(), h(10), SEXTA), { open: true, label: 'Aberta até 19:00' })
  })

  test('limites: abre exatamente na abertura e fecha exatamente no fechamento', () => {
    assert.equal(shopHoursStatus(barbearia(), h(9), SEXTA).open, true)
    assert.equal(shopHoursStatus(barbearia(), h(18, 59), SEXTA).open, true)
    assert.deepEqual(shopHoursStatus(barbearia(), h(19), SEXTA), { open: false, label: 'Fechada, abre amanhã às 09:00' })
  })

  test('antes de abrir: abre hoje mais tarde', () => {
    assert.deepEqual(shopHoursStatus(barbearia(), h(8, 30), SEXTA), { open: false, label: 'Fechada, abre às 09:00' })
  })
})

describe('dias em que a barbearia não abre', () => {
  test('hoje fechado, amanhã aberto: fechada mesmo dentro do horário', () => {
    const status = shopHoursStatus(barbearia({ dias_funcionamento: [1, 2, 3, 4, 6] }), h(10), SEXTA)
    assert.deepEqual(status, { open: false, label: 'Fechada, abre amanhã às 09:00' })
  })

  test('hoje e o fim de semana fechados: abre na segunda', () => {
    const status = shopHoursStatus(barbearia({ dias_funcionamento: [1, 2, 3, 4] }), h(10), SEXTA)
    assert.deepEqual(status, { open: false, label: 'Fechada, abre segunda às 09:00' })
  })

  test('sábado depois do fechamento com domingo fechado: não promete abrir amanhã', () => {
    const status = shopHoursStatus(barbearia({ dias_funcionamento: [1, 2, 3, 4, 5, 6] }), h(20), SABADO)
    assert.deepEqual(status, { open: false, label: 'Fechada, abre segunda às 09:00' })
  })

  test('só abre um dia por semana: depois do fechamento, abre na semana seguinte', () => {
    const status = shopHoursStatus(barbearia({ dias_funcionamento: [5] }), h(19, 30), SEXTA)
    assert.deepEqual(status, { open: false, label: 'Fechada, abre sexta às 09:00' })
  })

  test('sem a configuração de dias (resposta antiga da API): vale o padrão, todos os dias', () => {
    const semDias = { horario_abertura: '09:00:00', horario_fechamento: '19:00:00' }
    assert.deepEqual(shopHoursStatus(semDias, h(10), SEXTA), { open: true, label: 'Aberta até 19:00' })
  })
})

describe('barbearia desativada', () => {
  test('o status mostra a desativação, mesmo num dia e horário de funcionamento', () => {
    assert.deepEqual(shopHoursStatus(barbearia({ ativo: false }), h(10), SEXTA), { open: false, label: 'Barbearia desativada' })
  })

  test('reativada, volta ao status pelo horário', () => {
    assert.equal(shopHoursStatus(barbearia({ ativo: true }), h(10), SEXTA).label, 'Aberta até 19:00')
  })
})

describe('mudança de configuração', () => {
  test('o mesmo instante muda de status quando os dias mudam', () => {
    const antes = shopHoursStatus(barbearia(), h(10), SEXTA)
    const depois = shopHoursStatus(barbearia({ dias_funcionamento: [1, 2, 3, 4] }), h(10), SEXTA)
    assert.equal(antes.open, true)
    assert.equal(depois.open, false)
  })
})

describe('coerência com o calendário de agendamento', () => {
  const configuracoes = [TODOS_OS_DIAS, [1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7], [5], [6, 7], [1, 3, 5]]
  const instantes = [h(0), h(8, 59), h(9), h(12), h(18, 59), h(19), h(23, 59)]
  const proximoDia = (label: string, hoje: string) => {
    const quando = label.match(/abre (\S+) às/)?.[1]
    if (!quando) return hoje
    if (quando === 'amanhã') return addDays(hoje, 1)
    const iso = WEEKDAYS.find((dia) => dia.name === quando)?.iso
    for (let offset = 1; offset <= 7; offset++) if (isoWeekday(addDays(hoje, offset)) === iso) return addDays(hoje, offset)
    throw new Error(`dia não reconhecido em "${label}"`)
  }

  test('aberta só em dia de funcionamento e dentro do horário; o dia prometido é aberto e é o primeiro aberto', () => {
    let casos = 0
    for (const dias of configuracoes) {
      const loja = barbearia({ dias_funcionamento: dias })
      for (let offset = 0; offset < 14; offset++) {
        const hoje = addDays(SEXTA, offset)
        for (const minuto of instantes) {
          const status = shopHoursStatus(loja, minuto, hoje)
          const esperadoAberto = isOpenOn(loja, hoje) && minuto >= h(9) && minuto < h(19)
          assert.equal(status.open, esperadoAberto, `${dias} ${hoje} ${minuto}`)
          if (!status.open) {
            const dia = proximoDia(status.label, hoje)
            assert.ok(isOpenOn(loja, dia), `${status.label} promete um dia fechado (${dia})`)
            // Abre hoje mais tarde só se hoje é dia de funcionamento e ainda não abriu
            assert.equal(dia === hoje, isOpenOn(loja, hoje) && minuto < h(9), `${dias} ${hoje} ${minuto}: ${status.label}`)
            // Nenhum dia de funcionamento entre amanhã e o dia prometido
            for (let k = 1; addDays(hoje, k) < dia; k++) {
              assert.ok(!isOpenOn(loja, addDays(hoje, k)), `${status.label}: pulou ${addDays(hoje, k)}, que é aberto`)
            }
          }
          casos++
        }
      }
    }
    assert.equal(casos, configuracoes.length * 14 * instantes.length)
  })
})
