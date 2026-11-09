from specs_parser import RAM, SSD, CPU, GPU, Case, AIOCooler, AirCooler, Motherboard, PSU
import unittest

TEST_PARAMS = dict(
    price_str="$0",
    category="test",
    subcategory="test",
    url="",
    source=""
)

class TestRAM(unittest.TestCase):

    def test_ram_parsing(self):
        name = "V-COLOR MANTA XSKY RGB DDR5-6000 32GB(16G*2)白(CL30)"
        ram = RAM(name, **TEST_PARAMS)

        self.assertEqual(ram.total_capacity_gb, 32)
        self.assertEqual(ram.quantity, 2)
        self.assertEqual(ram.generation, "DDR5")
        self.assertEqual(ram.frequency, 6000)
        self.assertEqual(ram.cas_latency, 30)
        

class TestSSD(unittest.TestCase):

    def test_ssd_parsing(self):
        name = "海盜船 Corsair MP700 PRO XT 2TB/M.2 PCIe Gen5/讀:14900M/寫:14500M/TLC/五年保"
        ssd = SSD(name, **TEST_PARAMS)

        self.assertEqual(ssd.capacity_gb, 2048)
        self.assertEqual(ssd.generation, 5)
        self.assertEqual(ssd.memory_type, "TLC")
        self.assertEqual(ssd.read_speed, 14900) 
        self.assertEqual(ssd.write_speed, 14500)


class TestPSU(unittest.TestCase):

    def test_psu_parsing(self):
        name = "海韻 FOCUS GX-850 ATX3(850W) 雙8/金牌/全模組/ATX3.1(PCIe 5.1)10年保, $4290 ◆ ★"
        psu = PSU(name, **TEST_PARAMS)

        self.assertEqual(psu.wattage, 850) 
        self.assertEqual(psu.efficiency_rating, "80 Plus Gold")
        self.assertEqual(psu.atx_standard, "ATX 3.1")
        self.assertEqual(psu.modular, "Full")


class TestCPU(unittest.TestCase):

    def test_cpu_model(self):
        name = "AMD Ryzen Threadripper PRO 9995WX/2.5GHz(Turbo 5.4GHz)/350W/96C192T/快取384MB/代理商三年保固"
        cpu = CPU(name, **TEST_PARAMS)

        self.assertEqual(cpu.model, "Ryzen Threadripper PRO 9995WX")


class TestGPU(unittest.TestCase):

    def test_gpu_parsing(self):
        name = "微星 RTX 5080 16G GAMING TRIO OC WHITE (std:2715MHz/三風扇/註冊五年保/白色/長33.8cm) 1      "
        gpu = GPU(name, **TEST_PARAMS)

        self.assertEqual(gpu.model, "GeForce RTX 5080")
        self.assertEqual(gpu.card_length_cm, "33.8")


class TestAIOCooler(unittest.TestCase):

    def test_aio_parsing(self):
        name = "喬思伯 TF3-360 白色版 4螢幕水冷/3.5吋液晶/一體式三螢幕風扇/厚:5.5/6年【WXZ】, $6990 ◆ ★"
        aio = AIOCooler(name, **TEST_PARAMS)

        self.assertEqual(aio.length_mm, 360)
        self.assertEqual(aio.thickness_cm, 5.5)


class TestAirCooler(unittest.TestCase):

    def test_aircooler_parsing(self):
        name = "保銳 ETS-TD60D ARGB 散熱器/6導管/高15.9/數位監控/雙塔雙扇/全黑化/TDP:280【WXZ】, $1690 ◆ ★"
        air = AirCooler(name, **TEST_PARAMS)

        self.assertEqual(air.height_cm, 15.9) 
        self.assertEqual(air.heat_sink_count, 2) 
        self.assertEqual(air.heat_pipe_count, 6)


class TestMotherboard(unittest.TestCase):

    def test_motherboard_parsing(self):
        name = "華碩 Z890 MAX GAMING WIFI7 (ATX/1P1C/Realtek 2.5Gb/Wi-Fi 7+BT 5.4/註冊五年保) 12+1+2+1相供電【12相(80A)、、4*M.2、USB TYPE C 20G】"

        mb = Motherboard(name, **TEST_PARAMS)

        self.assertEqual(mb.chipset, "Z890")
        self.assertEqual(mb.form_factor, "ATX")
        self.assertEqual(mb.reverse_connectors, False)


class TestCase(unittest.TestCase):

    def test_case_parsing(self):
        name = "旋剛 M30 RGB 玻璃透側機殼 (E-ATX/Type-C/內建風扇前1後1/顯卡380mm/塔散172mm)"
        case = Case(name, **TEST_PARAMS)

        self.assertEqual(case.cpu_height_cm, 17.2)
        self.assertEqual(case.gpu_length_cm, 38) 
        self.assertEqual(case.motherboard_form_factor, "E-ATX") 


if __name__ == "__main__":
    unittest.main()