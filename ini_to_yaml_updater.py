import os
import requests
import yaml


def fetch_ini_data(url):
    """从链接获取 ini 文件内容并返回有效行"""
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    return response.text.splitlines()


def process_ruleset(input_lines):
    """处理规则集数据并生成对应的输出"""
    ruleset_output, class_output, groups_output = [], [], []

    for line in input_lines:
        if line.startswith("ruleset="):
            parts = line.split(",")
            ruleset_name = parts[0].split("=")[1].strip()

            if len(parts) == 2:  # 处理两部分的情况
                url = parts[1].strip()
                if "final" in url.lower():
                    ruleset_output.append(f"  - MATCH,{ruleset_name}")
                    continue

                file_name = os.path.splitext(os.path.basename(url))[0].lower()  # 获取不带后缀的文件名
                ruleset_output.append(f"  - RULE-SET,{file_name}_class,{ruleset_name}")
                class_output.append(f"  {file_name}_class: {{!!merge <<: *class, url: \"{url}\"}}")

            elif len(parts) > 2:  # 处理多于两部分的情况
                part1 = parts[1].strip("[]")
                part2 = parts[2].strip("[]")
                additional_parts = [part.strip() for part in parts[3:] if part.strip()]

                ruleset_output.append(f"  - {part1},{part2},{ruleset_name}" +
                                      (f",{','.join(additional_parts)}" if additional_parts else ""))

        elif line.startswith("custom_proxy_group="):
            parts = line.split('`')
            if len(parts) >= 3:
                group_name = parts[0].split('=')[1].strip()
                group_type = parts[1].strip()
                proxies = [part.strip().strip('[]') for part in parts[2:] if part.strip() and part.strip() != ".*"]
                include_all = "true" if parts[-1].strip() == ".*" else "false"

                output_line = f"  - {{name: {group_name}, type: {group_type}, proxies: [{', '.join(proxies)}], include-all: {include_all}}}"
                groups_output.append(output_line)

    return "\n".join(ruleset_output), "\n".join(class_output), "\n".join(groups_output)


def update_yaml(yaml_content, rules_output, providers_output, proxy_groups_output):
    """更新 YAML 文件内容，保留锚点和其他内容"""
    yaml_lines = yaml_content.splitlines()
    new_yaml_lines = []
    in_section = None  # 用于跟踪当前处理的部分

    for line in yaml_lines:
        # 检查行是否以字母开头并包含冒号
        if line and line[0].isalpha() and ':' in line:
            in_section = line.split(':')[0].strip()  # 更新当前部分

        if line.startswith("rules:"):
            new_yaml_lines.append("rules:")  # 添加新的 rules 部分
            new_yaml_lines.append(rules_output)  # 替换内容
            in_section = "rules"  # 设置当前部分为 rules
            continue  # 跳过后续行
        elif line.startswith("rule-providers:"):
            new_yaml_lines.append("rule-providers:")  # 添加新的 rule-providers 部分
            new_yaml_lines.append(providers_output)  # 替换内容
            in_section = "rule-providers"  # 设置当前部分为 rule-providers
            continue  # 跳过后续行
        elif line.startswith("proxy-groups:"):
            new_yaml_lines.append("proxy-groups:")  # 添加新的 proxy-groups 部分
            new_yaml_lines.append(proxy_groups_output)  # 替换内容
            in_section = "proxy-groups"  # 设置当前部分为 proxy-groups
            continue  # 跳过后续行
        elif line.strip() == "":
            new_yaml_lines.append(line)  # 保持空行
        elif in_section == "dns":
            if "nameserver-policy" not in line:
                new_yaml_lines.append(line)
                continue
            else:
                in_section = "nameserver-policy"
                continue
        else:
            # 如果 in_section 为空或不在指定部分，则添加到新文件
            if in_section is None or in_section not in ["rules", "rule-providers", "proxy-groups", "nameserver-policy"]:
                new_yaml_lines.append(line)

    return "\n".join(new_yaml_lines)




def main():

    ini_url = "https://raw.githubusercontent.com/nikiiii0319/OPENCLASH/refs/heads/main/clashmini.ini"
    yaml_url = "https://raw.githubusercontent.com/qichiyuhub/rule/refs/heads/master/config/Clash/config.yaml"

    try:
        input_lines = fetch_ini_data(ini_url)  # 获取 ini 文件内容
        rules_output, providers_output, proxy_groups_output = process_ruleset(input_lines)  # 处理规则集和代理组

        yaml_response = requests.get(yaml_url)  # 获取 YAML 文件内容
        yaml_response.raise_for_status()  # 检查请求是否成功
        yaml_content = yaml_response.text

        updated_yaml = update_yaml(yaml_content, rules_output, providers_output, proxy_groups_output)  # 更新 YAML 内容

        output_filename = "output.yaml"
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(updated_yaml)  # 输出更新后的 YAML 文件

        print(f"已成功输出到文件: {output_filename}")

    except requests.RequestException as e:
        print(f"无法获取文件: {e}")
    except yaml.YAMLError as e:
        print(f"无法解析 YAML 文件: {e}")


if __name__ == "__main__":
    main()
