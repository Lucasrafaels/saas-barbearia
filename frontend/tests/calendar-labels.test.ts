/**
 * FE-21 — rótulos acessíveis dos dias do calendário de agendamento.
 *
 * Antes, dias que não eram "hoje" ou "amanhã" eram anunciados com a data
 * repetida ("Domingo, 15 de novembro, domingo, 15 de novembro"), porque a
 * comparação entre o rótulo relativo e a data longa diferenciava maiúsculas.
 */
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { addDays, dateChipLabel } from '../src/utils/format.ts'

const HOJE = '2026-11-13' // sexta-feira
const DIAS = /\b(segunda|terça|quarta|quinta|sexta|sábado|domingo)/gi

describe('rótulo de cada dia', () => {
  test('hoje e amanhã levam a referência relativa e a data uma única vez', () => {
    assert.equal(dateChipLabel(HOJE, { today: HOJE }), 'Hoje, sexta-feira, 13 de novembro')
    assert.equal(dateChipLabel('2026-11-14', { today: HOJE }), 'Amanhã, sábado, 14 de novembro')
  })

  test('os demais dias trazem a data uma única vez (o caso da auditoria)', () => {
    assert.equal(dateChipLabel('2026-11-15', { today: HOJE }), 'Domingo, 15 de novembro')
    assert.equal(dateChipLabel('2026-11-18', { today: HOJE }), 'Quarta-feira, 18 de novembro')
  })

  test('dia fechado informa que a barbearia não abre', () => {
    assert.equal(dateChipLabel('2026-11-15', { today: HOJE, closed: true }), 'Domingo, 15 de novembro, barbearia fechada')
    assert.equal(dateChipLabel(HOJE, { today: HOJE, closed: true }), 'Hoje, sexta-feira, 13 de novembro, barbearia fechada')
  })

  test('virada de ano', () => {
    assert.equal(dateChipLabel('2027-01-01', { today: '2026-12-31' }), 'Amanhã, sexta-feira, 1 de janeiro')
  })
})

describe('os 21 dias oferecidos no agendamento', () => {
  const dias = Array.from({ length: 21 }, (_, index) => addDays(HOJE, index))

  for (const closed of [false, true]) {
    test(`cada rótulo é único e não repete a data nem o dia da semana (fechado=${closed})`, () => {
      const rotulos = dias.map((key) => dateChipLabel(key, { today: HOJE, closed }))
      assert.equal(new Set(rotulos).size, rotulos.length)
      for (const [index, rotulo] of rotulos.entries()) {
        const dia = Number(dias[index].slice(8, 10))
        assert.equal(rotulo.match(new RegExp(`\\b${dia} de `, 'g'))?.length, 1, rotulo)
        assert.equal(rotulo.match(DIAS)?.length, 1, rotulo)
        assert.equal(rotulo.endsWith(', barbearia fechada'), closed, rotulo)
      }
    })
  }
})
