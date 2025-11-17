import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface ChartComponentProps {
  data: any[]
  type: 'bar' | 'pie' | 'line'
  xField: string
  yField: string
}

export default function ChartComponent({ data, type, xField, yField }: ChartComponentProps) {
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    const chart = echarts.init(chartRef.current)

    let option: any = {}

    if (type === 'bar') {
      option = {
        xAxis: {
          type: 'category',
          data: data.map((item) => item[xField]),
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            data: data.map((item) => item[yField]),
            type: 'bar',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#667eea' },
                { offset: 1, color: '#764ba2' },
              ]),
            },
          },
        ],
        tooltip: {
          trigger: 'axis',
        },
      }
    } else if (type === 'pie') {
      option = {
        tooltip: {
          trigger: 'item',
        },
        legend: {
          orient: 'vertical',
          left: 'left',
        },
        series: [
          {
            name: yField,
            type: 'pie',
            radius: '50%',
            data: data.map((item) => ({
              value: item[yField],
              name: item[xField],
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)',
              },
            },
          },
        ],
      }
    } else if (type === 'line') {
      option = {
        xAxis: {
          type: 'category',
          data: data.map((item) => item[xField]),
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            data: data.map((item) => item[yField]),
            type: 'line',
            smooth: true,
            itemStyle: {
              color: '#667eea',
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(102, 126, 234, 0.4)' },
                { offset: 1, color: 'rgba(102, 126, 234, 0)' },
              ]),
            },
          },
        ],
        tooltip: {
          trigger: 'axis',
        },
      }
    }

    chart.setOption(option)

    const handleResize = () => {
      chart.resize()
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [data, type, xField, yField])

  return <div ref={chartRef} style={{ width: '100%', height: '400px' }} />
}
